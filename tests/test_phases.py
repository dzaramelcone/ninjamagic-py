# tests/test_phases.py
import pytest

from ninjamagic import phases
from ninjamagic.phases import Phase, get_phase


def test_day_phase():
    """6am-6pm is day phase."""
    assert get_phase(hour=6) == Phase.DAY
    assert get_phase(hour=12) == Phase.DAY
    assert get_phase(hour=17) == Phase.DAY


def test_evening_phase():
    """6pm-11pm is evening phase."""
    assert get_phase(hour=18) == Phase.EVENING
    assert get_phase(hour=20) == Phase.EVENING
    assert get_phase(hour=22) == Phase.EVENING


def test_waves_phase():
    """11pm-1am is waves phase."""
    assert get_phase(hour=23) == Phase.WAVES
    assert get_phase(hour=0) == Phase.WAVES


def test_fade_phase():
    """1am-2am is fade phase."""
    assert get_phase(hour=1) == Phase.FADE


def test_rest_phase():
    """2am-6am is rest phase (nightstorm)."""
    assert get_phase(hour=2) == Phase.REST
    assert get_phase(hour=4) == Phase.REST
    assert get_phase(hour=5) == Phase.REST


def test_spawn_multiplier_day():
    """Day has low spawn rate."""
    from ninjamagic.phases import Phase, get_spawn_multiplier

    mult = get_spawn_multiplier(Phase.DAY)
    assert mult == 0.2  # Low but not zero


def test_spawn_multiplier_waves():
    """Waves phase has maximum spawn rate."""
    from ninjamagic.phases import Phase, get_spawn_multiplier

    mult = get_spawn_multiplier(Phase.WAVES)
    assert mult == 3.0  # Intense


def test_spawn_multiplier_rest():
    """Rest phase has no spawning."""
    from ninjamagic.phases import Phase, get_spawn_multiplier

    mult = get_spawn_multiplier(Phase.REST)
    assert mult == 0.0


def test_get_current_phase_from_clock():
    """Get current phase from a NightClock instance."""
    from datetime import datetime, timedelta, timezone

    from ninjamagic.nightclock import NightClock
    from ninjamagic.phases import Phase, get_current_phase

    # Create a clock at noon (12:00 EST)
    EST = timezone(timedelta(hours=-5), name="EST")
    dt = datetime(2026, 1, 10, 12, 0, 0, tzinfo=EST)
    clock = NightClock(dt=dt)

    phase = get_current_phase(clock)
    assert phase == Phase.DAY


def test_wave_intensity_peaks_at_midnight():
    # At midnight (hour=0, minute=0), intensity should be at peak (1.0)
    intensity = phases.get_wave_intensity(hour=0, minute=0)
    assert intensity == pytest.approx(1.0, abs=0.01)


def test_wave_intensity_zero_outside_waves():
    # During DAY phase, intensity should be 0
    assert phases.get_wave_intensity(hour=12, minute=0) == 0.0
    # During REST phase, intensity should be 0
    assert phases.get_wave_intensity(hour=3, minute=0) == 0.0
    # During EVENING, intensity should be 0
    assert phases.get_wave_intensity(hour=20, minute=0) == 0.0
