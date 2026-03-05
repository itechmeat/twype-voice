## Why

Voice (S09) and text chat (S11) pipelines work independently but lack coordinated mode switching. The LLM receives no signal about which mode the user is currently in, so responses have the same format regardless of channel. S12 requires that switching to text produces detailed, structured answers while switching to voice produces brief, conversational ones — within a single continuous dialogue stream.

## What Changes

- **Context Manager** — explicit mode tracking (current mode, previous mode, switch timestamp) replacing the implicit `ContextVar[bool]` approach. Single source of truth for the active input/output mode across the agent lifecycle.
- **Mode-aware prompt injection** — dynamic prompt layer that tells the LLM the current input mode, so it adapts response style: brief and conversational for voice, detailed and structured for text.
- **Shared conversation history with mode labels** — conversation context sent to the LLM includes mode markers so it understands the flow of mode switches and adapts accordingly.
- **Concurrent input coordination** — prevent race conditions when voice and text arrive simultaneously. Currently `text_reply_lock` only serializes text; voice input can interleave freely.

## Capabilities

### New Capabilities
- `mode-switching`: Context Manager that tracks active mode, coordinates voice/text transitions, injects mode awareness into LLM context, and handles concurrent input safely.

### Modified Capabilities
- `prompt-builder`: Add dynamic mode-aware prompt injection — the assembled prompt must include the current input mode so the LLM adapts response format.
- `text-chat-handler`: Integrate with Context Manager instead of standalone `ContextVar` for mode tracking and TTS suppression decisions.

## Impact

- `apps/agent/src/agent.py` — replace `_TEXT_MODE_ACTIVE` ContextVar with Context Manager; update `tts_node()` to consult it.
- `apps/agent/src/main.py` — wire Context Manager into data channel handler and voice pipeline event handlers; add concurrent input coordination.
- `apps/agent/src/prompts.py` — support dynamic mode injection when building the final prompt context.
- `apps/agent/src/datachannel.py` — no structural changes, but callers change how mode is determined.
- `apps/agent/src/transcript.py` — mode value sourced from Context Manager instead of hardcoded strings.
- `openspec/specs/prompt-builder/spec.md` — updated requirements for mode-aware prompt assembly.
- `openspec/specs/text-chat-handler/spec.md` — updated requirements for Context Manager integration.
- Tests: new mode-switching tests + updates to existing datachannel and prompt tests.
