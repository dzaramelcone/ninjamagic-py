# Anchor System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand anchors from simple markers to maintained structures with strength, decay, and stability radius.

**Architecture:** Anchors have strength (from sacrifice), fuel level, and decay rate. They create a stability radius that blocks terrain decay and mob spawning. Neglected anchors decay and eventually extinguish. The eternal anchor is a special case that cannot be extinguished.

**Tech Stack:** Python, esper ECS, signal bus

---

## Background

**Current state:**
- `Anchor` is an empty marker component
- Bonfires have `ProvidesHeat`, `ProvidesLight`, `Noun`, `Glyph`
- One hardcoded bonfire at (9, 4) in `world/state.py`
- `survive.py` checks for `Anchor` component for guaranteed rest

**Target state:**
- `Anchor` component has strength, fuel, decay properties
- Stability radius blocks terrain decay (already hooked in terrain.py)
- Fuel depletes over time, requiring maintenance
- Low fuel = smaller radius, faster decay
- Zero fuel = anchor extinguishes (unless eternal)

---

## Task 1: Expand Anchor Component

**Files:**
- Modify: `ninjamagic/component.py`
- Test: `tests/test_anchor.py`

**Step 1: Write the failing test**

```python
# tests/test_anchor.py
import pytest
from ninjamagic.component import Anchor

def test_anchor_has_properties():
    """Anchors have strength, fuel, and eternal flag."""
    anchor = Anchor(strength=1.0, fuel=100.0, eternal=False)

    assert anchor.strength == 1.0
    assert anchor.fuel == 100.0
    assert anchor.eternal is False
    assert anchor.max_fuel == 100.0  # Derived from initial


def test_anchor_defaults():
    """Anchors have sensible defaults."""
    anchor = Anchor()

    assert anchor.strength == 1.0
    assert anchor.fuel == 100.0
    assert anchor.eternal is False


def test_eternal_anchor():
    """Eternal anchors have special properties."""
    anchor = Anchor(eternal=True)

    assert anchor.eternal is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_anchor.py::test_anchor_has_properties -v`
Expected: FAIL with TypeError (Anchor takes no arguments)

**Step 3: Expand Anchor component**

```python
# ninjamagic/component.py - replace the Anchor class

@component(slots=True, kw_only=True)
class Anchor:
    """The entity is an anchor (bonfire) that creates a stability radius.

    Attributes:
        strength: Base strength from sacrifice (0.0-1.0). Affects radius size.
        fuel: Current fuel level (0.0-max_fuel). Depletes over time.
        max_fuel: Maximum fuel capacity.
        eternal: If True, never runs out of fuel (the genesis anchor).
    """
    strength: float = 1.0
    fuel: float = 100.0
    max_fuel: float = 100.0
    eternal: bool = False
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_anchor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/component.py tests/test_anchor.py
git commit -m "feat(anchor): expand Anchor component with strength, fuel, eternal"
```

---

## Task 2: Stability Radius Calculation

**Files:**
- Create: `ninjamagic/anchor.py`
- Test: `tests/test_anchor.py`

**Step 1: Write the failing test**

```python
# tests/test_anchor.py - add these tests

def test_stability_radius_full_strength():
    """Full strength anchor has maximum radius."""
    from ninjamagic.anchor import get_stability_radius, BASE_STABILITY_RADIUS

    anchor = Anchor(strength=1.0, fuel=100.0)
    radius = get_stability_radius(anchor)

    assert radius == BASE_STABILITY_RADIUS


def test_stability_radius_scales_with_strength():
    """Weaker anchors have smaller radius."""
    from ninjamagic.anchor import get_stability_radius, BASE_STABILITY_RADIUS

    weak = Anchor(strength=0.5, fuel=100.0)
    strong = Anchor(strength=1.0, fuel=100.0)

    assert get_stability_radius(weak) < get_stability_radius(strong)
    assert get_stability_radius(weak) == BASE_STABILITY_RADIUS * 0.5


def test_stability_radius_scales_with_fuel():
    """Low fuel reduces effective radius."""
    from ninjamagic.anchor import get_stability_radius

    full = Anchor(strength=1.0, fuel=100.0, max_fuel=100.0)
    half = Anchor(strength=1.0, fuel=50.0, max_fuel=100.0)
    empty = Anchor(strength=1.0, fuel=0.0, max_fuel=100.0)

    assert get_stability_radius(full) > get_stability_radius(half)
    assert get_stability_radius(half) > get_stability_radius(empty)
    assert get_stability_radius(empty) == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_anchor.py::test_stability_radius_full_strength -v`
Expected: FAIL with "No module named 'ninjamagic.anchor'"

**Step 3: Create anchor.py with radius calculation**

```python
# ninjamagic/anchor.py
"""Anchor system: stability radius, fuel, maintenance."""

import math
from ninjamagic.component import Anchor

# Base stability radius at full strength and fuel (in cells)
BASE_STABILITY_RADIUS = 24

# Minimum radius (below this, anchor provides no protection)
MIN_STABILITY_RADIUS = 4


def get_stability_radius(anchor: Anchor) -> float:
    """Calculate the stability radius for an anchor.

    Radius = BASE * strength * fuel_fraction
    Returns 0.0 if fuel is empty (anchor is out).
    """
    if anchor.fuel <= 0 and not anchor.eternal:
        return 0.0

    fuel_fraction = anchor.fuel / anchor.max_fuel if anchor.max_fuel > 0 else 1.0

    # Eternal anchors always have full fuel effect
    if anchor.eternal:
        fuel_fraction = 1.0

    radius = BASE_STABILITY_RADIUS * anchor.strength * fuel_fraction

    # If below minimum, return 0 (effectively dead)
    if radius < MIN_STABILITY_RADIUS and not anchor.eternal:
        return 0.0

    return radius
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_anchor.py -k stability_radius -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/anchor.py tests/test_anchor.py
git commit -m "feat(anchor): add stability radius calculation"
```

---

## Task 3: Fuel Consumption

**Files:**
- Modify: `ninjamagic/anchor.py`
- Test: `tests/test_anchor.py`

**Step 1: Write the failing test**

```python
# tests/test_anchor.py - add these tests

def test_fuel_consumption():
    """Anchors consume fuel over time."""
    from ninjamagic.anchor import consume_fuel, FUEL_CONSUMPTION_RATE

    anchor = Anchor(strength=1.0, fuel=100.0, max_fuel=100.0)

    # Consume fuel for 1 second
    consume_fuel(anchor, seconds=1.0)

    assert anchor.fuel == 100.0 - FUEL_CONSUMPTION_RATE


def test_fuel_consumption_stops_at_zero():
    """Fuel doesn't go negative."""
    from ninjamagic.anchor import consume_fuel

    anchor = Anchor(strength=1.0, fuel=1.0, max_fuel=100.0)

    # Consume more than available
    consume_fuel(anchor, seconds=1000.0)

    assert anchor.fuel == 0.0


def test_eternal_anchor_no_consumption():
    """Eternal anchors don't consume fuel."""
    from ninjamagic.anchor import consume_fuel

    anchor = Anchor(strength=1.0, fuel=100.0, eternal=True)

    consume_fuel(anchor, seconds=1000.0)

    assert anchor.fuel == 100.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_anchor.py::test_fuel_consumption -v`
Expected: FAIL with "cannot import name 'consume_fuel'"

**Step 3: Implement fuel consumption**

```python
# ninjamagic/anchor.py - add constants and function

# Fuel consumed per second (100 fuel = ~16 minutes at base rate)
FUEL_CONSUMPTION_RATE = 0.1


def consume_fuel(anchor: Anchor, *, seconds: float) -> None:
    """Consume fuel from an anchor over time.

    Does nothing for eternal anchors.
    """
    if anchor.eternal:
        return

    consumption = FUEL_CONSUMPTION_RATE * seconds
    anchor.fuel = max(0.0, anchor.fuel - consumption)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_anchor.py -k fuel_consumption -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/anchor.py tests/test_anchor.py
git commit -m "feat(anchor): add fuel consumption"
```

---

## Task 4: Add Fuel (Tending)

**Files:**
- Modify: `ninjamagic/anchor.py`
- Modify: `ninjamagic/bus.py`
- Test: `tests/test_anchor.py`

**Step 1: Write the failing test**

```python
# tests/test_anchor.py - add these tests

def test_add_fuel():
    """Players can add fuel to anchors."""
    from ninjamagic.anchor import add_fuel

    anchor = Anchor(strength=1.0, fuel=50.0, max_fuel=100.0)

    add_fuel(anchor, amount=25.0)

    assert anchor.fuel == 75.0


def test_add_fuel_caps_at_max():
    """Fuel can't exceed max_fuel."""
    from ninjamagic.anchor import add_fuel

    anchor = Anchor(strength=1.0, fuel=90.0, max_fuel=100.0)

    add_fuel(anchor, amount=50.0)

    assert anchor.fuel == 100.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_anchor.py::test_add_fuel -v`
Expected: FAIL with "cannot import name 'add_fuel'"

**Step 3: Implement add_fuel**

```python
# ninjamagic/anchor.py - add function

def add_fuel(anchor: Anchor, *, amount: float) -> float:
    """Add fuel to an anchor.

    Returns the amount actually added (may be less if near max).
    """
    old_fuel = anchor.fuel
    anchor.fuel = min(anchor.max_fuel, anchor.fuel + amount)
    return anchor.fuel - old_fuel
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_anchor.py -k add_fuel -v`
Expected: PASS

**Step 5: Add TendAnchor signal**

```python
# ninjamagic/bus.py - add signal

@frozen
class TendAnchor(Signal):
    """Player tends an anchor, adding fuel."""
    source: int  # Player entity
    anchor: int  # Anchor entity
    fuel_amount: float
```

**Step 6: Commit**

```bash
git add ninjamagic/anchor.py ninjamagic/bus.py tests/test_anchor.py
git commit -m "feat(anchor): add fuel tending"
```

---

## Task 5: Anchor Processor

**Files:**
- Modify: `ninjamagic/anchor.py`
- Test: `tests/test_anchor.py`

**Step 1: Write the failing test**

```python
# tests/test_anchor.py - add this test

def test_anchor_processor():
    """Anchor processor consumes fuel and handles tending."""
    import esper
    from ninjamagic.anchor import process
    from ninjamagic.component import Anchor, Transform
    from ninjamagic import bus

    esper.clear_database()

    # Create an anchor
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Anchor(strength=1.0, fuel=100.0, max_fuel=100.0))
    esper.add_component(anchor_eid, Transform(map_id=1, y=0, x=0))

    # Process for 10 seconds
    process(delta_seconds=10.0)
    bus.clear()

    anchor = esper.component_for_entity(anchor_eid, Anchor)
    assert anchor.fuel < 100.0  # Fuel consumed
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_anchor.py::test_anchor_processor -v`
Expected: FAIL with "cannot import name 'process'"

**Step 3: Implement anchor processor**

```python
# ninjamagic/anchor.py - add process function

import esper
from ninjamagic import bus
from ninjamagic.component import Transform


def process(*, delta_seconds: float) -> None:
    """Process all anchors: consume fuel, handle tending signals."""

    # Handle tending signals
    for sig in bus.receive(bus.TendAnchor):
        if esper.has_component(sig.anchor, Anchor):
            anchor = esper.component_for_entity(sig.anchor, Anchor)
            added = add_fuel(anchor, amount=sig.fuel_amount)
            # Could emit a signal here for feedback

    # Consume fuel from all anchors
    for eid, anchor in esper.get_component(Anchor):
        consume_fuel(anchor, seconds=delta_seconds)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_anchor.py::test_anchor_processor -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/anchor.py tests/test_anchor.py
git commit -m "feat(anchor): add anchor processor"
```

---

## Task 6: Integrate with Terrain Decay

**Files:**
- Modify: `ninjamagic/terrain.py`
- Modify: `ninjamagic/anchor.py`

**Step 1: Create function to get all anchor positions with radii**

```python
# ninjamagic/anchor.py - add function

def get_anchor_positions_with_radii() -> list[tuple[int, int, float]]:
    """Get all anchor positions with their stability radii.

    Returns list of (y, x, radius) tuples.
    """
    result = []

    for eid, (anchor, transform) in esper.get_components(Anchor, Transform):
        radius = get_stability_radius(anchor)
        if radius > 0:
            result.append((transform.y, transform.x, radius))

    return result
```

**Step 2: Update terrain.py to use variable radii**

```python
# ninjamagic/terrain.py - modify get_decay_rate and process

def get_decay_rate(*, map_id: int, y: int, x: int,
                   anchor_positions: list[tuple[int, int, float]]) -> float:
    """Calculate decay rate at a position based on distance from anchors.

    anchor_positions is list of (y, x, radius) tuples.
    Returns 0.0 (no decay) to 1.0 (maximum decay).
    """
    if not anchor_positions:
        return 1.0

    # Find nearest anchor and check if inside its radius
    for ay, ax, radius in anchor_positions:
        dist = math.sqrt((y - ay) ** 2 + (x - ax) ** 2)
        if dist <= radius:
            return 0.0

    # Outside all radii = full decay
    # (Could add gradient based on nearest anchor, but keeping simple for now)
    return 1.0


def process(now: Looptime) -> None:
    """Main terrain processor - call from game loop."""
    from ninjamagic.anchor import get_anchor_positions_with_radii

    # Gather all anchor positions with their radii
    anchor_positions = get_anchor_positions_with_radii()

    # Run decay
    process_decay(now=now, anchor_positions=anchor_positions)
```

**Step 3: Update tests to use new signature**

Update any tests that call `get_decay_rate` to pass `(y, x, radius)` tuples instead of `(y, x)` tuples.

**Step 4: Commit**

```bash
git add ninjamagic/terrain.py ninjamagic/anchor.py tests/test_terrain.py
git commit -m "feat(anchor): integrate variable radii with terrain decay"
```

---

## Task 7: Integrate Anchor Processor into Game Loop

**Files:**
- Modify: `ninjamagic/state.py`

**Step 1: Add anchor processing to game loop**

```python
# ninjamagic/state.py - add import
from ninjamagic import anchor

# In State.step(), track delta time and call anchor processor
# Add before terrain processing:
anchor.process(delta_seconds=self.delta)
```

**Step 2: Ensure delta time is available**

Check that `State` has a `delta` property or calculate it:

```python
# If not already present in State:
self.delta = 1.0 / 240.0  # At 240 TPS
```

**Step 3: Commit**

```bash
git add ninjamagic/state.py
git commit -m "feat(anchor): integrate anchor processor into game loop"
```

---

## Task 8: Update Eternal Anchor

**Files:**
- Modify: `ninjamagic/world/state.py`

**Step 1: Mark the starting bonfire as eternal**

```python
# ninjamagic/world/state.py - update bonfire creation

bonfire = esper.create_entity(
    Transform(map_id=map_id, y=9, x=4),
    Anchor(strength=1.0, fuel=100.0, max_fuel=100.0, eternal=True),  # Mark as eternal
    ProvidesHeat(),
    ProvidesLight(),
    Noun(value="bonfire", pronoun=Pronouns.IT),
)
```

**Step 2: Commit**

```bash
git add ninjamagic/world/state.py
git commit -m "feat(anchor): mark starting bonfire as eternal"
```

---

## Task 9: Tend Command

**Files:**
- Modify: `ninjamagic/commands.py`
- Test: Manual testing

**Step 1: Add tend command**

Find the command registration area in `commands.py` and add:

```python
# ninjamagic/commands.py - add tend command

@register("tend", "tend fire", "tend bonfire", "add fuel")
def cmd_tend(eid: int, args: str) -> None:
    """Add fuel to a nearby anchor."""
    transform = esper.component_for_entity(eid, Transform)

    # Find nearby anchors
    for anchor_eid, (anchor, anchor_transform) in esper.get_components(Anchor, Transform):
        if anchor_transform.map_id != transform.map_id:
            continue

        # Check if close enough (within 2 tiles)
        dy = abs(transform.y - anchor_transform.y)
        dx = abs(transform.x - anchor_transform.x)

        if dy <= 2 and dx <= 2:
            # Check if player has fuel item (wood, etc.)
            # For now, just add fuel directly
            FUEL_PER_TEND = 25.0

            bus.pulse(bus.TendAnchor(
                source=eid,
                anchor=anchor_eid,
                fuel_amount=FUEL_PER_TEND,
            ))

            noun = esper.component_for_entity(anchor_eid, Noun)
            story.echo("{0} {0:tend} the {1}.", eid, noun.value)
            return

    story.echo("There's nothing to tend here.", source=eid)
```

**Step 2: Manual test**

Run the server and verify `tend` command works near the bonfire.

**Step 3: Commit**

```bash
git add ninjamagic/commands.py
git commit -m "feat(anchor): add tend command"
```

---

## Summary

After completing all tasks, you will have:

1. **Expanded Anchor component** - strength, fuel, max_fuel, eternal properties
2. **Stability radius calculation** - based on strength and fuel level
3. **Fuel consumption** - anchors deplete fuel over time
4. **Fuel tending** - players can add fuel to anchors
5. **Anchor processor** - handles fuel and tending each tick
6. **Terrain integration** - decay respects variable anchor radii
7. **Eternal anchor** - starting bonfire never runs out
8. **Tend command** - players can maintain anchors

**Dependencies:** This plan depends on Task 3 of the Terrain System plan (decay rate calculation).

**Next plan:** Mob Spawning (spawn from unlit tiles, path toward anchors)
