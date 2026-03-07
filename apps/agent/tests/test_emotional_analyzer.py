from __future__ import annotations

import pytest
from emotional_analyzer import (
    EmotionalTrendTracker,
    classify_quadrant,
    estimate_circumplex,
    get_tone_guidance,
)


class TestEstimateCircumplex:
    def test_negative_sentiment_with_exclamations(self) -> None:
        valence, arousal = estimate_circumplex(-0.7, "THIS IS TERRIBLE!!! WHY?!")
        assert valence == pytest.approx(-0.7)
        assert arousal > 0.3

    def test_positive_sentiment_calm_text(self) -> None:
        valence, arousal = estimate_circumplex(0.5, "everything is going well today")
        assert valence == pytest.approx(0.5)
        assert arousal < 0.3

    def test_sentiment_none_defaults_valence_zero(self) -> None:
        valence, _arousal = estimate_circumplex(None, "some text here")
        assert valence == 0.0

    def test_empty_text_arousal_zero(self) -> None:
        valence, arousal = estimate_circumplex(0.3, "")
        assert valence == pytest.approx(0.3)
        assert arousal == 0.0

    def test_whitespace_text_arousal_zero(self) -> None:
        valence, arousal = estimate_circumplex(None, "   ")
        assert valence == 0.0
        assert arousal == 0.0

    def test_valence_clamped(self) -> None:
        valence, _arousal = estimate_circumplex(1.5, "text")
        assert valence == 1.0

        valence, _arousal = estimate_circumplex(-1.5, "text")
        assert valence == -1.0

    def test_ellipsis_reduces_arousal(self) -> None:
        _v1, arousal_no_ellipsis = estimate_circumplex(None, "I see")
        _v2, arousal_with_ellipsis = estimate_circumplex(None, "I see... well... hmm...")
        assert arousal_with_ellipsis < arousal_no_ellipsis

    def test_longer_words_increase_arousal_signal(self) -> None:
        _v1, arousal_short = estimate_circumplex(None, "calm words only")
        _v2, arousal_long = estimate_circumplex(
            None,
            "hyperventilation disorientation dysregulation",
        )
        assert arousal_long > arousal_short


class TestClassifyQuadrant:
    def test_distress(self) -> None:
        assert classify_quadrant(-0.6, 0.7) == "distress"

    def test_melancholy(self) -> None:
        assert classify_quadrant(-0.5, -0.4) == "melancholy"

    def test_serenity(self) -> None:
        assert classify_quadrant(0.4, -0.3) == "serenity"

    def test_excitement(self) -> None:
        assert classify_quadrant(0.6, 0.5) == "excitement"

    def test_neutral(self) -> None:
        assert classify_quadrant(0.1, -0.05) == "neutral"

    def test_custom_threshold(self) -> None:
        assert classify_quadrant(0.3, 0.3, threshold=0.5) == "neutral"
        assert classify_quadrant(0.6, 0.6, threshold=0.5) == "excitement"


class TestGetToneGuidance:
    def test_distress(self) -> None:
        result = get_tone_guidance("distress")
        assert "empathetic" in result.lower()

    def test_neutral(self) -> None:
        result = get_tone_guidance("neutral")
        assert "balanced" in result.lower()

    def test_all_quadrants_return_string(self) -> None:
        for quadrant in ("distress", "melancholy", "serenity", "excitement", "neutral"):
            assert isinstance(get_tone_guidance(quadrant), str)
            assert len(get_tone_guidance(quadrant)) > 0


class TestEmotionalTrendTracker:
    def test_few_snapshots_returns_stable(self) -> None:
        tracker = EmotionalTrendTracker()
        tracker.add_snapshot(0.5, 0.5)
        tracker.add_snapshot(0.6, 0.6)
        v_trend, a_trend = tracker.get_trends()
        assert v_trend == "stable"
        assert a_trend == "stable"

    def test_rising_trend(self) -> None:
        tracker = EmotionalTrendTracker(trend_threshold=0.05)
        for i in range(6):
            tracker.add_snapshot(-0.5 + i * 0.2, 0.0)
        v_trend, _a_trend = tracker.get_trends()
        assert v_trend == "rising"

    def test_falling_trend(self) -> None:
        tracker = EmotionalTrendTracker(trend_threshold=0.05)
        for i in range(6):
            tracker.add_snapshot(0.5 - i * 0.2, 0.0)
        v_trend, _a_trend = tracker.get_trends()
        assert v_trend == "falling"

    def test_stable_trend(self) -> None:
        tracker = EmotionalTrendTracker()
        for _ in range(6):
            tracker.add_snapshot(0.5, 0.3)
        v_trend, a_trend = tracker.get_trends()
        assert v_trend == "stable"
        assert a_trend == "stable"

    def test_window_eviction(self) -> None:
        tracker = EmotionalTrendTracker(max_size=3)
        tracker.add_snapshot(0.1, 0.1)
        tracker.add_snapshot(0.2, 0.2)
        tracker.add_snapshot(0.3, 0.3)
        tracker.add_snapshot(0.4, 0.4)
        assert len(tracker.snapshots) == 3

    def test_empty_tracker_returns_stable(self) -> None:
        tracker = EmotionalTrendTracker()
        v_trend, a_trend = tracker.get_trends()
        assert v_trend == "stable"
        assert a_trend == "stable"

    def test_high_distress_activates_for_three_distress_snapshots_with_falling_valence(
        self,
    ) -> None:
        tracker = EmotionalTrendTracker(trend_threshold=0.05)
        tracker.add_snapshot(-0.2, 0.4)
        tracker.add_snapshot(-0.45, 0.5)
        tracker.add_snapshot(-0.7, 0.6)

        assert tracker.high_distress is True

    def test_high_distress_deactivates_when_latest_snapshot_is_not_distress(self) -> None:
        tracker = EmotionalTrendTracker(trend_threshold=0.05)
        tracker.add_snapshot(-0.2, 0.4)
        tracker.add_snapshot(-0.45, 0.5)
        tracker.add_snapshot(-0.7, 0.6)
        tracker.add_snapshot(0.2, 0.2)

        assert tracker.high_distress is False

    def test_high_distress_requires_falling_valence_trend(self) -> None:
        tracker = EmotionalTrendTracker(trend_threshold=0.05)
        tracker.add_snapshot(-0.7, 0.6)
        tracker.add_snapshot(-0.6, 0.7)
        tracker.add_snapshot(-0.5, 0.8)

        assert tracker.high_distress is False
