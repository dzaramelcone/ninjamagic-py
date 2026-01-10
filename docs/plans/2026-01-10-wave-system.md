# Wave System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement time-based spawn rate scaling - mobs spawn more frequently at night, peaking during wave hours (11pm-1am).

**Architecture:** The spawn system queries the NightClock to determine current phase (day/evening/waves/fade/rest). Spawn rate multiplier varies by phase. During wave hours, mobs spawn rapidly and path aggressively toward anchors.

**Tech Stack:** Python, esper ECS, NightClock

---

## Background

**Current state:**
- NightClock tracks game time (hour, minute, in_nightstorm)
- Spawn system uses a flat spawn_rate
- No time-based behavior

**Target state:**
- Time phases: Day (6am-6pm), Evening (6pm-11pm), Waves (11pm-1am), Fade (1am-2am), Rest (2am-6am)
- Spawn rate multiplier varies by phase
- Wave phase has intense spawning
- Rest phase has no spawning

---

## Task 1: Time Phase Detection

**Files:**
- Create: `ninjamagic/phases.py`
- Test: `tests/test_phases.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_phases.py::test_day_phase -v`
Expected: FAIL with "No module named 'ninjamagic.phases'"

**Step 3: Create phases.py**

```python
# ninjamagic/phases.py
"""Time phases for the day/night cycle."""

from enum import Enum


class Phase(Enum):
    """Phases of the day/night cycle."""
    DAY = "day"          # 6am-6pm: Safe to venture
    EVENING = "evening"  # 6pm-11pm: Tension rises, head back
    WAVES = "waves"      # 11pm-1am: Peak mob spawning, defend
    FADE = "fade"        # 1am-2am: Waves die off, eat
    REST = "rest"        # 2am-6am: Camp triggers, XP consolidates


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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_phases.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/phases.py tests/test_phases.py
git commit -m "feat(phases): add time phase detection"
```

---

## Task 2: Spawn Rate Multipliers

**Files:**
- Modify: `ninjamagic/phases.py`
- Test: `tests/test_phases.py`

**Step 1: Write the failing test**

```python
# tests/test_phases.py - add these tests

def test_spawn_multiplier_day():
    """Day has low spawn rate."""
    from ninjamagic.phases import get_spawn_multiplier, Phase

    mult = get_spawn_multiplier(Phase.DAY)
    assert mult == 0.2  # Low but not zero


def test_spawn_multiplier_waves():
    """Waves phase has maximum spawn rate."""
    from ninjamagic.phases import get_spawn_multiplier, Phase

    mult = get_spawn_multiplier(Phase.WAVES)
    assert mult == 3.0  # Intense


def test_spawn_multiplier_rest():
    """Rest phase has no spawning."""
    from ninjamagic.phases import get_spawn_multiplier, Phase

    mult = get_spawn_multiplier(Phase.REST)
    assert mult == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_phases.py::test_spawn_multiplier_day -v`
Expected: FAIL with "cannot import name 'get_spawn_multiplier'"

**Step 3: Implement spawn multipliers**

```python
# ninjamagic/phases.py - add this

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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_phases.py -k spawn_multiplier -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/phases.py tests/test_phases.py
git commit -m "feat(phases): add spawn rate multipliers by phase"
```

---

## Task 3: Integrate Phases with Spawn System

**Files:**
- Modify: `ninjamagic/spawn.py`
- Test: `tests/test_spawn.py`

**Step 1: Write the failing test**

```python
# tests/test_spawn.py - add this test

def test_spawn_respects_phase_multiplier():
    """Spawn rate is multiplied by phase multiplier."""
    import esper
    from ninjamagic.spawn import process_spawning, SpawnConfig
    from ninjamagic.component import Mob, Transform, Anchor
    from ninjamagic.phases import Phase

    esper.clear_database()

    map_id = esper.create_entity()

    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=50, x=50))
    esper.add_component(anchor_eid, Anchor(strength=1.0, fuel=100.0))

    config = SpawnConfig(spawn_rate=10.0, max_mobs=100)
    walkable = lambda y, x: True

    # During REST phase, no mobs should spawn
    process_spawning(
        map_id=map_id,
        delta_seconds=10.0,
        config=config,
        walkable_check=walkable,
        phase=Phase.REST,
    )

    rest_mobs = len(list(esper.get_component(Mob)))

    # During WAVES phase, many mobs should spawn
    esper.clear_database()
    map_id = esper.create_entity()
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=50, x=50))
    esper.add_component(anchor_eid, Anchor(strength=1.0, fuel=100.0))

    process_spawning(
        map_id=map_id,
        delta_seconds=10.0,
        config=config,
        walkable_check=walkable,
        phase=Phase.WAVES,
    )

    waves_mobs = len(list(esper.get_component(Mob)))

    assert rest_mobs == 0
    assert waves_mobs > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spawn.py::test_spawn_respects_phase_multiplier -v`
Expected: FAIL with "unexpected keyword argument 'phase'"

**Step 3: Update spawn processor to accept phase**

```python
# ninjamagic/spawn.py - modify process_spawning signature and logic

from ninjamagic.phases import Phase, get_spawn_multiplier


def process_spawning(
    *,
    map_id: int,
    delta_seconds: float,
    config: SpawnConfig,
    walkable_check: Callable[[int, int], bool],
    phase: Phase = Phase.DAY,  # Add phase parameter
) -> list[int]:
    """Process mob spawning for a map.

    Returns list of newly spawned mob entity IDs.
    """
    spawned = []

    # Apply phase multiplier
    multiplier = get_spawn_multiplier(phase)
    if multiplier == 0.0:
        return spawned  # No spawning during this phase

    # ... rest of function, but modify the accumulator line:
    _spawn_accumulators[map_id] += delta_seconds * config.spawn_rate * multiplier

    # ... rest unchanged
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spawn.py::test_spawn_respects_phase_multiplier -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/spawn.py tests/test_spawn.py
git commit -m "feat(spawn): integrate phase-based spawn multipliers"
```

---

## Task 4: Get Current Phase from NightClock

**Files:**
- Modify: `ninjamagic/phases.py`
- Test: `tests/test_phases.py`

**Step 1: Write the failing test**

```python
# tests/test_phases.py - add this test

def test_get_current_phase_from_clock():
    """Get current phase from a NightClock instance."""
    from ninjamagic.phases import get_current_phase
    from ninjamagic.nightclock import NightClock, NightTime

    # Create a clock at noon
    clock = NightClock()
    clock = clock.replace(NightTime(hour=12, minute=0))

    phase = get_current_phase(clock)
    assert phase == Phase.DAY
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_phases.py::test_get_current_phase_from_clock -v`
Expected: FAIL with "cannot import name 'get_current_phase'"

**Step 3: Implement get_current_phase**

```python
# ninjamagic/phases.py - add import and function

from ninjamagic.nightclock import NightClock


def get_current_phase(clock: NightClock) -> Phase:
    """Get the current phase from a NightClock instance."""
    return get_phase(hour=clock.hour)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_phases.py::test_get_current_phase_from_clock -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/phases.py tests/test_phases.py
git commit -m "feat(phases): add get_current_phase from NightClock"
```

---

## Task 5: Integrate with Game Loop

**Files:**
- Modify: `ninjamagic/state.py`

**Step 1: Update game loop to pass current phase**

```python
# ninjamagic/state.py - modify spawn call

from ninjamagic.phases import get_current_phase

# In State.step(), where process_spawning is called:
current_phase = get_current_phase(self.clock)  # Assuming State has a clock

spawn.process_spawning(
    map_id=...,
    delta_seconds=self.delta,
    config=spawn_config,
    walkable_check=walkable,
    phase=current_phase,
)
```

**Step 2: Commit**

```bash
git add ninjamagic/state.py
git commit -m "feat(wave): pass current phase to spawn processor"
```

---

## Task 6: Phase Transition Signals

**Files:**
- Modify: `ninjamagic/bus.py`
- Modify: `ninjamagic/phases.py`

**Step 1: Add phase change signal**

```python
# ninjamagic/bus.py - add signal

@frozen
class PhaseChanged(Signal):
    """The day/night phase has changed."""
    old_phase: str  # Phase enum value
    new_phase: str
```

**Step 2: Track and emit phase changes**

```python
# ninjamagic/phases.py - add phase tracking

from ninjamagic import bus

_last_phase: Phase | None = None


def process_phase_changes(clock: NightClock) -> Phase:
    """Check for phase changes and emit signals.

    Returns the current phase.
    """
    global _last_phase

    current = get_current_phase(clock)

    if _last_phase is not None and current != _last_phase:
        bus.pulse(bus.PhaseChanged(
            old_phase=_last_phase.value,
            new_phase=current.value,
        ))

    _last_phase = current
    return current
```

**Step 3: Integrate into game loop**

```python
# ninjamagic/state.py - use process_phase_changes

from ninjamagic.phases import process_phase_changes

# In State.step():
current_phase = process_phase_changes(self.clock)
```

**Step 4: Commit**

```bash
git add ninjamagic/bus.py ninjamagic/phases.py ninjamagic/state.py
git commit -m "feat(phases): emit signals on phase transitions"
```

---

## Task 7: Wave Announcement

**Files:**
- Modify: `ninjamagic/phases.py`

**Step 1: Add handler for phase transitions**

```python
# ninjamagic/phases.py - add announcement handler

from ninjamagic import story


def process_announcements() -> None:
    """Announce phase transitions to players."""
    for sig in bus.receive(bus.PhaseChanged):
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
```

**Step 2: Integrate into game loop**

```python
# ninjamagic/state.py - call process_announcements

from ninjamagic.phases import process_announcements

# In State.step(), after phase change detection:
process_announcements()
```

**Step 3: Commit**

```bash
git add ninjamagic/phases.py ninjamagic/state.py
git commit -m "feat(wave): announce phase transitions to players"
```

---

## Task 8: Wave Intensity Gradient

**Files:**
- Modify: `ninjamagic/phases.py`
- Test: `tests/test_phases.py`

**Step 1: Write the failing test**

```python
# tests/test_phases.py - add this test

def test_wave_intensity_peaks_at_midnight():
    """Wave intensity is highest at midnight, lower at edges."""
    from ninjamagic.phases import get_wave_intensity

    # 11pm - start of waves
    intensity_11pm = get_wave_intensity(hour=23, minute=0)

    # Midnight - peak
    intensity_midnight = get_wave_intensity(hour=0, minute=0)

    # 12:30am - past peak
    intensity_1230 = get_wave_intensity(hour=0, minute=30)

    assert intensity_midnight > intensity_11pm
    assert intensity_midnight > intensity_1230


def test_wave_intensity_zero_outside_waves():
    """Wave intensity is zero outside wave phase."""
    from ninjamagic.phases import get_wave_intensity

    assert get_wave_intensity(hour=12, minute=0) == 0.0
    assert get_wave_intensity(hour=2, minute=0) == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_phases.py::test_wave_intensity_peaks_at_midnight -v`
Expected: FAIL with "cannot import name 'get_wave_intensity'"

**Step 3: Implement wave intensity**

```python
# ninjamagic/phases.py - add function

import math


def get_wave_intensity(*, hour: int, minute: int) -> float:
    """Get the current wave intensity (0.0 to 1.0).

    Peaks at midnight, ramps up from 11pm, down to 1am.
    Zero outside wave hours.
    """
    phase = get_phase(hour=hour)
    if phase != Phase.WAVES:
        return 0.0

    # Convert to minutes since 11pm
    if hour == 23:
        minutes_since_start = minute
    else:  # hour == 0
        minutes_since_start = 60 + minute

    # Wave phase is 2 hours = 120 minutes
    # Peak at 60 minutes (midnight)
    peak_minute = 60

    # Use cosine for smooth curve
    # At start (0): intensity = 0.5
    # At peak (60): intensity = 1.0
    # At end (120): intensity = 0.5
    progress = minutes_since_start / 120.0  # 0 to 1
    angle = progress * math.pi  # 0 to pi
    intensity = (1.0 - math.cos(angle)) / 2.0  # 0 -> 1 -> 0

    return intensity
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_phases.py -k wave_intensity -v`
Expected: PASS

**Step 5: Optionally integrate intensity into spawn rate**

```python
# ninjamagic/spawn.py - optionally use intensity for finer control

# During WAVES phase, multiply by intensity for smoother ramp
if phase == Phase.WAVES:
    from ninjamagic.phases import get_wave_intensity
    intensity = get_wave_intensity(hour=clock.hour, minute=clock.minute)
    multiplier *= (0.5 + 0.5 * intensity)  # Range: 1.5x to 3.0x
```

**Step 6: Commit**

```bash
git add ninjamagic/phases.py tests/test_phases.py
git commit -m "feat(wave): add wave intensity gradient peaking at midnight"
```

---

## Summary

After completing all tasks, you will have:

1. **Time phase detection** - Day/Evening/Waves/Fade/Rest based on hour
2. **Spawn rate multipliers** - different intensity by phase
3. **Spawn integration** - spawn processor uses phase multipliers
4. **NightClock integration** - get phase from game clock
5. **Game loop integration** - phase passed to spawning
6. **Phase transition signals** - notify when phase changes
7. **Announcements** - broadcast messages on phase changes
8. **Wave intensity gradient** - smooth intensity curve during waves

**Dependencies:** Requires Mob Spawning plan.

**Next plan:** Mob Phenotypes (different mob types and behaviors)
