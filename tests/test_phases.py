# tests/test_phases.py
import pytest
from ninjamagic.phases import get_phase, Phase

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
