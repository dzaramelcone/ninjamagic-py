import re

from ninjamagic.util import TickStats

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def test_tick_stats_histogram_and_late_ticks():
    stats = TickStats(
        step=0.01,
        alpha=0.5,
        bucket_edges_ms=(4.0, 6.0, 10.0),
        frame_budget_ms=8.0,
    )

    stats.record(tick_duration=0.003, jitter=0.0)
    stats.record(tick_duration=0.010, jitter=0.0)
    stats.record(tick_duration=0.012, jitter=0.0)
    stats.record(tick_duration=0.020, jitter=0.0)

    snapshot = stats.snapshot_and_reset()
    counts = snapshot.bucket_counts

    assert snapshot.total_ticks == 4
    assert snapshot.late_ticks == 1
    assert counts[0] == 1
    assert counts[2] == 1
    assert counts[-1] == 2
    assert sum(counts) == 4

    rendered = str(snapshot)
    assert "\x1b[32m" in rendered
    assert "\x1b[31m" in rendered
    cleaned = ANSI_RE.sub("", rendered)
    assert "0-4ms" in cleaned
    assert "10ms+" in cleaned


def test_late_ticks_use_budget_threshold():
    stats = TickStats(
        step=0.01,
        alpha=0.5,
        bucket_edges_ms=(4.0, 8.0, 16.0),
        frame_budget_ms=8.0,
    )

    stats.record(tick_duration=0.007, jitter=0.0)
    stats.record(tick_duration=0.009, jitter=0.0)
    stats.record(tick_duration=0.016, jitter=0.0)
    stats.record(tick_duration=0.017, jitter=0.0)

    snapshot = stats.snapshot_and_reset()

    assert snapshot.late_ticks == 1

    assert stats.total_ticks == 0
    assert stats.late_ticks == 0
    assert stats.bucket_counts == [0] * len(snapshot.bucket_counts)
