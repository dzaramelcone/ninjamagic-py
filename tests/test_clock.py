import calendar
import math
from datetime import datetime, timedelta

import pytest

from ninjamagic.nightclock import (
    BASE_NIGHTYEAR,
    EPOCH,
    NIGHTS_PER_DAY,
    SECONDS_PER_NIGHT,
    SECONDS_PER_NIGHT_ACTIVE,
    SECONDS_PER_NIGHT_HOUR,
    SECONDS_PER_NIGHTSTORM,
    SECONDS_PER_NIGHTSTORM_HOUR,
    UTC,
    NightClock,
    NightDelta,
    NightTime,
)


def utc(dt: datetime) -> datetime:
    """Ensure a datetime is in UTC with tzinfo set."""
    if dt.tzinfo:
        return dt.astimezone(UTC)
    return dt.replace(tzinfo=UTC)


def test_epoch_baseline():
    nc = NightClock(EPOCH)

    assert nc.seconds_since_epoch == 0
    assert nc.moons_since_epoch == 0
    assert nc.nights_since_dt_midnight == 0
    assert nc.nights_since_epoch == 0
    assert nc.nights_this_nightyear == 0

    assert nc.nightyears == BASE_NIGHTYEAR


def test_nights_per_day_consistency():
    # Move forward exactly one real day
    next_day = utc(EPOCH + timedelta(days=1))
    nc = NightClock(next_day)

    assert nc.moons_since_epoch == 1
    # At exactly midnight next day, seconds_since_midnight == 0,
    # so nights_since_midnight == 0 again.
    assert nc.nights_since_dt_midnight == 0
    # Total nights since epoch advanced by NIGHTS_PER_DAY
    assert nc.nights_since_epoch == NIGHTS_PER_DAY


def test_nightyears_increment_with_month():
    # Dec 1 2025 -> BASE_NIGHTYEAR
    nc_dec = NightClock(utc(datetime(2025, 12, 1, 0, 0, 0)))
    # Jan 1 2026 -> BASE_NIGHTYEAR + 1
    nc_jan = NightClock(utc(datetime(2026, 1, 1, 0, 0, 0)))

    assert nc_dec.nightyears == BASE_NIGHTYEAR
    assert nc_jan.nightyears == BASE_NIGHTYEAR + 1

    # nights_this_nightyear should reset on month change
    assert nc_dec.nights_this_nightyear == 0
    assert nc_jan.nights_this_nightyear == 0


# --- Time-of-night / hour mapping ------------------------------------


def test_hours_at_start_mid_end_of_night():
    # Start of night (midnight) -> 06:00
    start = utc(datetime(2025, 12, 1, 0, 0, 0))
    nc_start = NightClock(start)
    assert nc_start.seconds == 0
    assert nc_start.hour == 6

    # Middle of night -> around 16:00
    mid = utc(EPOCH + timedelta(seconds=SECONDS_PER_NIGHT_ACTIVE / 2))
    nc_mid = NightClock(mid)
    assert math.isclose(nc_mid.elapsed_pct, 0.5, rel_tol=1e-6)
    assert 15 <= nc_mid.hour <= 17  # allow a 1h band due to flooring

    # Very end of night (just before wrap) -> between 01:00 and 02:00
    end = utc(EPOCH + timedelta(seconds=SECONDS_PER_NIGHT_ACTIVE - 1))
    nc_end = NightClock(end)
    assert 1 <= nc_end.hour <= 2


def test_minutes_and_next_hour_eta_consistency():
    # Pick 3 in-game hours into the active night:
    # 3 * SECONDS_PER_NIGHT_HOUR after midnight
    dt = utc(EPOCH + timedelta(seconds=3 * SECONDS_PER_NIGHT_HOUR))
    nc = NightClock(dt)

    assert nc.hour == 9  # 06 + 3
    assert nc.minute == 0  # exactly on the hour

    # next_hour_eta should be exactly one in-game hour of real seconds
    assert math.isclose(nc.next_hour_eta, SECONDS_PER_NIGHT_HOUR, rel_tol=1e-6)


# --- Nightstorm behavior ---------------------------------------------


def test_nightstorm_flags_and_eta_before_and_during():
    # Just before nightstorm starts
    storm_start_real_offset = SECONDS_PER_NIGHT - SECONDS_PER_NIGHTSTORM
    before_storm = utc(EPOCH + timedelta(seconds=storm_start_real_offset - 1))
    nc_before = NightClock(before_storm)

    assert not nc_before.in_nightstorm
    assert 0 < nc_before.nightstorm_eta <= 2  # within a couple of seconds

    # Inside nightstorm window
    during_storm = utc(EPOCH + timedelta(seconds=storm_start_real_offset + 1))
    nc_during = NightClock(during_storm)

    assert nc_during.in_nightstorm
    assert 0.0 < nc_during.nightstorm_elapsed_pct <= 1.0

    # ETA should now be negative since it started
    assert nc_during.nightstorm_eta < 0


# --- Year progression / brightness -----------------------------------


def test_year_elapsed_pct_bounds():
    # At exact start of month -> 0
    start_month = utc(datetime(2025, 12, 1, 0, 0, 0))
    nc_start = NightClock(start_month)
    assert math.isclose(nc_start.nightyear_elapsed_pct, 0.0, rel_tol=1e-6)

    # Half way through month (approx) -> ~0.5
    mid_month = utc(datetime(2025, 12, 16, 12, 0, 0))
    nc_mid = NightClock(mid_month)
    assert 0.3 < nc_mid.nightyear_elapsed_pct < 0.7  # loose band

    # End of month (just before next month) -> close to 1
    end_month = utc(datetime(2025, 12, 31, 23, 59, 59))
    nc_end = NightClock(end_month)
    assert 0.8 < nc_end.nightyear_elapsed_pct <= 1.0


GOLDEN_MONTHS = [(2025 + y, m) for y in range(4) for m in range(1, 13)]
SEASON_FRACS = [0.0, 0.25, 0.5, 0.75, 1.0]
NIGHT_FRACS = [0.0, 0.25, 0.5, 0.75, 0.9]


def test_brightness_index_golden(golden_json):
    def format_sample(season_frac, night_frac, nc):
        return (
            f"season={season_frac:.2f} "
            f"hour={night_frac:.2f}::{nc.hours_float:05.2f} "
            f"icon={nc.brightness_index} "
            f"d={nc.dawn:.2f} "
            f"k={nc.dusk:.2f} "
            f"iso={nc.dt.strftime("%m/%d %H%M")}"
        )

    results: list[dict[str, object]] = []

    for y, m in GOLDEN_MONTHS:
        days_in_month = calendar.monthrange(y, m)[1]

        # Build lines of the grid; each line is NIGHT_FRAC row containing SEASON_FRAC columns.
        lines: list[str] = []

        for night_frac in NIGHT_FRACS:
            row_entries = []

            for season_frac in SEASON_FRACS:
                # Determine which real day corresponds to this season sample
                d = 1 + int((days_in_month - 1) * season_frac)

                # Sample at night-fraction progression
                base_midnight = datetime(y, m, d, 0, 0, 0, tzinfo=UTC)
                dt = base_midnight + timedelta(
                    seconds=night_frac * SECONDS_PER_NIGHT,
                )

                nc = NightClock(dt)
                row_entries.append(format_sample(season_frac, night_frac, nc))

            # Join row entries into one line
            lines.append(" | ".join(row_entries))

        # The entire 2D grid becomes ONE string

        results.append(
            {
                "year": y,
                "month": m,
                "grid": lines,
            }
        )

    golden_json(results)


storm_start = 1.0 - SECONDS_PER_NIGHTSTORM / SECONDS_PER_NIGHT

STORM_FRACS = [
    storm_start,
    storm_start + (1.0 - storm_start) * 0.25,
    storm_start + (1.0 - storm_start) * 0.5,
    storm_start + (1.0 - storm_start) * 0.75,
    0.999999,
]


@pytest.mark.parametrize("year, month", GOLDEN_MONTHS)
@pytest.mark.parametrize("frac", STORM_FRACS)
def test_nightstorm_always_zero(year, month, frac):
    """
    For time in any (year, month) in the nightstorm window,
    brightness_index must be 0.
    """
    base_midnight = datetime(year, month, 15, 0, 0, 0, tzinfo=UTC)
    dt = base_midnight + timedelta(seconds=frac * SECONDS_PER_NIGHT)

    nc = NightClock(dt)

    assert nc.in_nightstorm, f"{dt=}: expected in_nightstorm=True, got False"
    assert nc.brightness_index == 0, (
        f"{dt=}: expected brightness_index=0 during nightstorm, "
        f"got {nc.brightness_index}"
    )


def test_to_cycle_seconds_active():
    t = NightTime(6, 00)
    assert t.total_seconds() == 0.0

    t = NightTime(7, 00)
    expected = SECONDS_PER_NIGHT_HOUR
    assert t.total_seconds() == pytest.approx(expected)

    t = NightTime(1, 00)
    assert t.total_seconds() == pytest.approx(19 * SECONDS_PER_NIGHT_HOUR)

    t = NightTime(2, 00)
    assert t.total_seconds() == pytest.approx(SECONDS_PER_NIGHT_ACTIVE)

    # 03:00 -> Start of Storm + 1 Storm Hour (~6.25s)
    t = NightTime(3, 00)
    expected = SECONDS_PER_NIGHT_ACTIVE + SECONDS_PER_NIGHTSTORM_HOUR
    assert t.total_seconds() == pytest.approx(expected)


def test_round_trip_conversion():
    original = NightTime(22, 15)
    seconds = original.total_seconds()
    reconstructed = NightTime.from_seconds(seconds)

    assert original.hour == reconstructed.hour
    assert original.minute == reconstructed.minute

    original_storm = NightTime(4, 12)
    seconds_storm = original_storm.total_seconds()
    reconstructed_storm = NightTime.from_seconds(seconds_storm)

    assert original_storm.hour == reconstructed_storm.hour
    assert original_storm.minute == reconstructed_storm.minute


def test_integration_add_to_clock():
    """Verify Delta can be added to NightClock."""
    clock = NightClock(EPOCH)  # 06:00
    delta = NightDelta(seconds=100.0)  # 100 real seconds

    future_clock = clock + delta

    # Verify the clock moved forward by exactly delta.total_seconds
    assert (future_clock.dt - clock.dt).total_seconds() == 100.0
    assert future_clock.seconds == 100.0


def test_comparisons():
    t1 = NightTime(23, 0)
    t2 = NightTime(0, 0)  # 00:00 is technically "later" in the night than 23:00
    t3 = NightTime(2, 0)  # 02:00 is even later (storm start)

    assert t1 < t2
    assert t2 < t3
    assert t1 != t2


def test_clock_initialization():
    clock = NightClock(EPOCH)
    assert clock.hour == 6
    assert clock.minute == 0
    assert clock.seconds == 0.0
    assert clock.in_nightstorm is False


def test_storm_transition():
    """Check behavior exactly at the storm boundary."""
    clock = NightClock(EPOCH + timedelta(seconds=SECONDS_PER_NIGHT_ACTIVE))

    assert clock.in_nightstorm is True
    assert clock.hour == 2
    assert clock.minute == 0

    # Check storm percentage
    assert clock.nightstorm_elapsed_pct == 0.0


@pytest.mark.parametrize("hour", list(range(24)))
def test_next_event_logic(hour):
    clock = NightClock(EPOCH).replace(NightTime(hour))
    target = NightTime((hour + 1) % 24, 0)
    delta = clock.next(target)
    expected_delta = SECONDS_PER_NIGHT_HOUR
    if 2 <= hour < 6:
        expected_delta = SECONDS_PER_NIGHTSTORM_HOUR
    assert delta.total_seconds() == pytest.approx(expected_delta)


@pytest.mark.parametrize("hour", list(range(24)))
def test_next_event_wraps_cycle(hour):
    target_hour = (hour - 1) % 24
    clock = NightClock(EPOCH).replace(NightTime(hour, 0))
    target = NightTime(target_hour, 0)

    delta = clock.next(target)

    seconds_elapsed = SECONDS_PER_NIGHT_HOUR
    if 2 <= target_hour < 6:
        seconds_elapsed = SECONDS_PER_NIGHTSTORM_HOUR
    expected_wait = SECONDS_PER_NIGHT - seconds_elapsed
    assert delta.total_seconds() == pytest.approx(expected_wait)


def test_arithmetic():
    clock = NightClock(EPOCH)

    # Add a Delta of 1 Real Second
    delta = NightDelta(seconds=1.0)
    new_clock = clock + delta
    assert (new_clock.dt - clock.dt).total_seconds() == 1.0

    # Subtract two clocks
    diff = new_clock - clock
    assert isinstance(diff, NightDelta)
    assert diff.total_seconds() == 1.0


def test_next_storm_wraps_cycle():
    """
    Scenario: It is 05:00 (Deep Storm). When is the next 03:00?
    Logic: Next night. We must finish this storm, wait through active, then hit storm.
    """
    clock = NightClock(EPOCH).replace(NightTime(5, 0))
    current_seconds = SECONDS_PER_NIGHT_ACTIVE + (3 * SECONDS_PER_NIGHTSTORM_HOUR)
    target = NightTime(3, 0)
    target_seconds = SECONDS_PER_NIGHT_ACTIVE + SECONDS_PER_NIGHTSTORM_HOUR
    delta = clock.next(target)
    remaining_in_cycle = SECONDS_PER_NIGHT - current_seconds
    expected = remaining_in_cycle + target_seconds
    assert delta.total_seconds() == pytest.approx(expected)
