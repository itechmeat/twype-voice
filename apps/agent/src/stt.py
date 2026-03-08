from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import aiohttp
from livekit import rtc
from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    stt,
)
from livekit.agents.types import NOT_GIVEN, NotGivenOr
from livekit.agents.utils import AudioBuffer
from livekit.plugins import deepgram
from livekit.plugins.deepgram import stt as deepgram_stt
from livekit.plugins.deepgram.log import logger as deepgram_logger
from settings import AgentSettings


def _merge_query_params(url: str, params: dict[str, str | bool]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(
        {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in params.items()
        }
    )
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment)
    )


def _extract_average_sentiment(payload: dict[str, Any]) -> float | None:
    channel = payload.get("channel")
    if not isinstance(channel, dict):
        channel = payload

    alternatives = channel.get("alternatives")
    if (
        not isinstance(alternatives, list)
        or not alternatives
        or not isinstance(alternatives[0], dict)
    ):
        return None

    sentiments = alternatives[0].get("sentiments")
    if not isinstance(sentiments, list):
        return None

    scores = [
        float(item["sentiment"])
        for item in sentiments
        if isinstance(item, dict) and isinstance(item.get("sentiment"), (int, float))
    ]
    if not scores:
        return None

    return sum(scores) / len(scores)


def _attach_sentiment(event: stt.SpeechEvent, payload: dict[str, Any]) -> stt.SpeechEvent:
    sentiment_raw = _extract_average_sentiment(payload)
    if sentiment_raw is not None:
        event.sentiment_raw = sentiment_raw  # type: ignore[attr-defined]
    return event


class TwypeDeepgramSpeechStream(deepgram_stt.SpeechStream):
    async def _connect_ws(self) -> aiohttp.ClientWebSocketResponse:
        live_config: dict[str, Any] = {
            "model": self._opts.model,
            "punctuate": self._opts.punctuate,
            "smart_format": self._opts.smart_format,
            "no_delay": self._opts.no_delay,
            "interim_results": self._opts.interim_results,
            "encoding": "linear16",
            "vad_events": self._opts.vad_events,
            "sample_rate": self._opts.sample_rate,
            "channels": self._opts.num_channels,
            "endpointing": False if self._opts.endpointing_ms == 0 else self._opts.endpointing_ms,
            "filler_words": self._opts.filler_words,
            "profanity_filter": self._opts.profanity_filter,
            "numerals": self._opts.numerals,
            "mip_opt_out": self._opts.mip_opt_out,
            "sentiment": True,
        }
        if self._opts.enable_diarization:
            live_config["diarize"] = True
        if self._opts.keywords:
            live_config["keywords"] = self._opts.keywords
        if self._opts.keyterm:
            live_config["keyterm"] = self._opts.keyterm
        if self._opts.language:
            live_config["language"] = self._opts.language
        if self._opts.tags:
            live_config["tag"] = self._opts.tags

        try:
            ws = await asyncio.wait_for(
                self._session.ws_connect(
                    _merge_query_params(
                        deepgram_stt._to_deepgram_url(
                            live_config,
                            base_url=self._opts.endpoint_url,
                            websocket=True,
                        ),
                        {"sentiment": True},
                    ),
                    headers={"Authorization": f"Token {self._api_key}"},
                ),
                self._conn_options.timeout,
            )
            ws_headers = {
                key: value
                for key, value in ws._response.headers.items()
                if key.startswith("dg-") or key == "Date"
            }
            deepgram_logger.debug(
                "Established new Deepgram STT WebSocket connection:",
                extra={"headers": ws_headers},
            )
        except (aiohttp.ClientConnectorError, TimeoutError) as exc:
            raise APIConnectionError("failed to connect to deepgram") from exc
        return ws

    def _process_stream_event(self, data: dict) -> None:
        if self._opts.language is None:
            raise RuntimeError("Deepgram streaming requires an explicit language")

        if data["type"] == "SpeechStarted":
            if self._speaking:
                return

            self._speaking = True
            self._event_ch.send_nowait(stt.SpeechEvent(type=stt.SpeechEventType.START_OF_SPEECH))
            return

        if data["type"] == "Results":
            metadata = data["metadata"]
            request_id = metadata["request_id"]
            is_final_transcript = data["is_final"]
            is_endpoint = data["speech_final"]
            self._request_id = request_id

            alts = deepgram_stt.live_transcription_to_speech_data(
                self._opts.language,
                data,
                is_final=is_final_transcript,
                start_time_offset=self.start_time_offset,
            )
            if len(alts) > 0 and alts[0].text:
                if not self._speaking:
                    self._speaking = True
                    self._event_ch.send_nowait(stt.SpeechEvent(type=stt.SpeechEventType.START_OF_SPEECH))

                if is_final_transcript:
                    final_event = stt.SpeechEvent(
                        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                        request_id=request_id,
                        alternatives=alts,
                    )
                    self._event_ch.send_nowait(_attach_sentiment(final_event, data))
                else:
                    self._event_ch.send_nowait(
                        stt.SpeechEvent(
                            type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                            request_id=request_id,
                            alternatives=alts,
                        )
                    )

            if is_endpoint and self._speaking:
                self._speaking = False
                self._event_ch.send_nowait(stt.SpeechEvent(type=stt.SpeechEventType.END_OF_SPEECH))
            return

        if data["type"] != "Metadata":
            deepgram_logger.warning("received unexpected message from deepgram %s", data)


class TwypeDeepgramSTT(deepgram.STT):
    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[deepgram_stt.DeepgramLanguages | str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        config = self._sanitize_options(language=language)

        recognize_config = {
            "model": str(config.model),
            "punctuate": config.punctuate,
            "detect_language": config.detect_language,
            "smart_format": config.smart_format,
            "keywords": self._opts.keywords,
            "profanity_filter": config.profanity_filter,
            "numerals": config.numerals,
            "mip_opt_out": config.mip_opt_out,
            "sentiment": True,
        }
        if config.enable_diarization:
            deepgram_logger.warning(
                "speaker diarization is not supported in non-streaming mode, ignoring"
            )
        if config.language:
            recognize_config["language"] = config.language

        try:
            async with self._ensure_session().post(
                url=_merge_query_params(
                    deepgram_stt._to_deepgram_url(
                        recognize_config,
                        self._opts.endpoint_url,
                        websocket=False,
                    ),
                    {"sentiment": True},
                ),
                data=rtc.combine_audio_frames(buffer).to_wav_bytes(),
                headers={
                    "Authorization": f"Token {self._api_key}",
                    "Accept": "application/json",
                    "Content-Type": "audio/wav",
                },
                timeout=aiohttp.ClientTimeout(
                    total=30,
                    sock_connect=conn_options.timeout,
                ),
            ) as response:
                payload = await response.json()
                event = deepgram_stt.prerecorded_transcription_to_speech_event(
                    config.language,
                    payload,
                )

                results = payload.get("results")
                channels = results.get("channels") if isinstance(results, dict) else None
                if not isinstance(channels, list) or not channels:
                    deepgram_logger.warning(
                        "Deepgram prerecorded response missing expected"
                        " results.channels structure: %s",
                        payload,
                    )
                    return event

                return _attach_sentiment(event, channels[0])
        except TimeoutError as exc:
            raise APITimeoutError() from exc
        except aiohttp.ClientResponseError as exc:
            raise APIStatusError(
                message=exc.message,
                status_code=exc.status,
                request_id=None,
                body=None,
            ) from exc
        except Exception as exc:
            raise APIConnectionError() from exc

    def stream(
        self,
        *,
        language: NotGivenOr[deepgram_stt.DeepgramLanguages | str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> TwypeDeepgramSpeechStream:
        config = self._sanitize_options(language=language)
        stream = TwypeDeepgramSpeechStream(
            stt=self,
            conn_options=conn_options,
            opts=config,
            api_key=self._api_key,
            http_session=self._ensure_session(),
            base_url=self._opts.endpoint_url,
        )
        self._streams.add(stream)
        return stream


def build_stt(settings: AgentSettings) -> deepgram.STT:
    return TwypeDeepgramSTT(
        api_key=settings.DEEPGRAM_API_KEY,
        model=settings.STT_MODEL,
        language=settings.STT_LANGUAGE,
    )
