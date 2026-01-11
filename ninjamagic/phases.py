# ninjamagic/phases.py
"""Time phases for the day/night cycle."""

import math
from enum import Enum

from ninjamagic import bus, story
from ninjamagic.nightclock import NightClock

_last_phase: "Phase | None" = None


class Phase(Enum):
    """Phases of the day/night cycle."""

    DAY = "day"  # 6am-6pm: Safe to venture
    EVENING = "evening"  # 6pm-11pm: Tension rises, head back
    WAVES = "waves"  # 11pm-1am: Peak mob spawning, defend
    FADE = "fade"  # 1am-2am: Waves die off, eat
    REST = "rest"  # 2am-6am: Camp triggers, XP consolidates


# Spawn rate multipliers by phase
SPAWN_MULTIPLIERS = {
    Phase.DAY: 0.2,  # Mobs exist but manageable
    Phase.EVENING: 0.8,  # Tension rises
    Phase.WAVES: 3.0,  # Peak intensity
    Phase.FADE: 0.5,  # Waves dying off
    Phase.REST: 0.0,  # No spawning during rest
}


def get_spawn_multiplier(phase: Phase) -> float:
    """Get the spawn rate multiplier for a phase."""
    return SPAWN_MULTIPLIERS.get(phase, 1.0)


def get_wave_intensity(*, hour: int, minute: int) -> float:
    """Return wave intensity (0.0-1.0) based on time.

    Peaks at midnight (1.0), ramps from 11pm to 1am.
    Zero outside wave hours.
    """
    phase = get_phase(hour=hour)
    if phase != Phase.WAVES:
        return 0.0

    # Calculate minutes since 11pm (start of WAVES)
    minutes_since_start = minute if hour == 23 else 60 + minute

    # Map to 0-1 progress through the 2-hour wave period
    progress = minutes_since_start / 120.0

    # Sine curve: 0 at start, 1 at middle (midnight), 0 at end
    intensity = math.sin(progress * math.pi)

    return intensity


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


def process_phase_changes(clock: NightClock) -> Phase:
    """Check for phase changes and emit signals.

    Returns the current phase.
    """
    global _last_phase

    current = get_current_phase(clock)

    if _last_phase is not None and current != _last_phase:
        bus.pulse(
            bus.PhaseChanged(
                old_phase=_last_phase.value,
                new_phase=current.value,
            )
        )

    _last_phase = current
    return current


def process_announcements() -> None:
    """Announce phase transitions to players."""
    for sig in bus.iter(bus.PhaseChanged):
        if sig.new_phase == Phase.EVENING.value:
            story.broadcast("The sun dips low. Darkness stirs.")

        elif sig.new_phase == Phase.WAVES.value:
            story.broadcast("The darkness surges. They come for the light.")

        elif sig.new_phase == Phase.FADE.value:
            story.broadcast("The wave recedes. Catch your breath.")

        elif sig.new_phase == Phase.REST.value:
            story.broadcast("The night quiets. Rest now, if you can.")

        elif sig.new_phase == Phase.DAY.value:
            story.broadcast("Dawn breaks. The darkness retreats.")
