from __future__ import annotations

import asyncio

import pytest
from silence_timer import SilenceTimer


@pytest.fixture()
def tracker():
    class CallTracker:
        def __init__(self):
            self.short_count = 0
            self.long_count = 0
            self.short_event = asyncio.Event()
            self.long_event = asyncio.Event()

        async def on_short(self):
            self.short_count += 1
            self.short_event.set()

        async def on_long(self):
            self.long_count += 1
            self.long_event.set()

    return CallTracker()


@pytest.mark.asyncio()
async def test_short_callback_fires(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.15,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    await asyncio.wait_for(tracker.short_event.wait(), timeout=1.0)
    assert tracker.short_count == 1
    assert tracker.long_count == 0
    timer.stop()


@pytest.mark.asyncio()
async def test_long_callback_fires(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.1,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    await asyncio.wait_for(tracker.long_event.wait(), timeout=1.0)
    assert tracker.short_count == 1
    assert tracker.long_count == 1
    timer.stop()


@pytest.mark.asyncio()
async def test_reset_cancels_pending(tracker):
    timer = SilenceTimer(
        short_timeout=0.1,
        long_timeout=0.2,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    await asyncio.sleep(0.05)
    timer.reset()
    await asyncio.sleep(0.08)
    assert tracker.short_count == 0
    timer.stop()


@pytest.mark.asyncio()
async def test_reset_after_short_cancels_long(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.2,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    await asyncio.wait_for(tracker.short_event.wait(), timeout=1.0)
    assert tracker.short_count == 1
    timer.reset()
    await asyncio.sleep(0.03)
    assert tracker.long_count == 0
    timer.stop()


@pytest.mark.asyncio()
async def test_stop_cancels_all(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.1,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    await asyncio.sleep(0.02)
    timer.stop()
    await asyncio.sleep(0.1)
    assert tracker.short_count == 0
    assert tracker.long_count == 0


@pytest.mark.asyncio()
async def test_stop_is_idempotent(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.1,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    assert timer.is_running
    timer.stop()
    timer.stop()
    assert not timer.is_running


@pytest.mark.asyncio()
async def test_single_fire_guard_no_duplicate_short(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.15,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    await asyncio.wait_for(tracker.short_event.wait(), timeout=1.0)
    await asyncio.sleep(0.05)
    assert tracker.short_count == 1
    timer.stop()


@pytest.mark.asyncio()
async def test_reset_clears_fired_guard(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.1,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.start()
    await asyncio.wait_for(tracker.long_event.wait(), timeout=1.0)
    assert tracker.short_count == 1
    assert tracker.long_count == 1

    tracker.short_event.clear()
    tracker.long_event.clear()
    timer.reset()
    await asyncio.wait_for(tracker.short_event.wait(), timeout=1.0)
    assert tracker.short_count == 2
    timer.stop()


@pytest.mark.asyncio()
async def test_has_fired_property(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.1,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    assert not timer.has_fired
    timer.start()
    await asyncio.wait_for(tracker.short_event.wait(), timeout=1.0)
    assert timer.has_fired
    timer.reset()
    assert not timer.has_fired
    timer.stop()


def test_invalid_timeouts(tracker):
    with pytest.raises(ValueError, match="short_timeout must be positive"):
        SilenceTimer(
            short_timeout=0,
            long_timeout=1.0,
            on_short_timeout=tracker.on_short,
            on_long_timeout=tracker.on_long,
        )

    with pytest.raises(ValueError, match="long_timeout must be greater"):
        SilenceTimer(
            short_timeout=5.0,
            long_timeout=3.0,
            on_short_timeout=tracker.on_short,
            on_long_timeout=tracker.on_long,
        )


@pytest.mark.asyncio()
async def test_reset_on_stopped_timer_does_nothing(tracker):
    timer = SilenceTimer(
        short_timeout=0.05,
        long_timeout=0.1,
        on_short_timeout=tracker.on_short,
        on_long_timeout=tracker.on_long,
    )
    timer.stop()
    timer.reset()
    await asyncio.sleep(0.1)
    assert tracker.short_count == 0
    assert not timer.is_running
