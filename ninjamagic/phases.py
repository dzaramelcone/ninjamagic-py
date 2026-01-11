# ninjamagic/phases.py
"""Time phases for the day/night cycle."""

from enum import Enum

from ninjamagic.nightclock import NightClock


class Phase(Enum):
    """Phases of the day/night cycle."""
    DAY = "day"          # 6am-6pm: Safe to venture
    EVENING = "evening"  # 6pm-11pm: Tension rises, head back
    WAVES = "waves"      # 11pm-1am: Peak mob spawning, defend
    FADE = "fade"        # 1am-2am: Waves die off, eat
    REST = "rest"        # 2am-6am: Camp triggers, XP consolidates


# Spawn rate multipliers by phase
SPAWN_MULTIPLIERS = {
    Phase.DAY: 0.2,      # Mobs exist but manageable
    Phase.EVENING: 0.8,  # Tension rises
    Phase.WAVES: 3.0,    # Peak intensity
    Phase.FADE: 0.5,     # Waves dying off
    Phase.REST: 0.0,     # No spawning during rest
}


def get_spawn_multiplier(phase: Phase) -> float:
    """Get the spawn rate multiplier for a phase."""
    return SPAWN_MULTIPLIERS.get(phase, 1.0)


def get_phase(*, hour: int) -> Phase:
    """Get the current phase based on hour (0-23).

    Phase boundaries:
    - Day: 6am (6) to 6pm (18)
    - Evening: 6pm (18) to 11pm (23)
    - Waves: 11pm (23) to 1am (1)
    - Fade: 1am (1) to 2am (2)
    - Rest: 2am (2) to 6am (6)
    """
    if 6 <= hour < 18:
        return Phase.DAY
    if 18 <= hour < 23:
        return Phase.EVENING
    if hour == 23 or hour == 0:
        return Phase.WAVES
    if hour == 1:
        return Phase.FADE
    # 2, 3, 4, 5
    return Phase.REST


def get_current_phase(clock: NightClock) -> Phase:
    """Get the current phase from a NightClock instance."""
    return get_phase(hour=clock.hour)
