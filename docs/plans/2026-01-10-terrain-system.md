# Terrain System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement lazy terrain instantiation and decay mechanics - the foundation for "darkness as entropy."

**Architecture:** Terrain tiles are lazily generated when first visited. Once instantiated, decay begins immediately. Decay rate is a function of distance from anchors. Tiles mutate toward hostile states over time unless within an anchor's stability radius.

**Tech Stack:** Python, esper ECS, signal bus

---

## Background

**Current state:**
- Maps use `Chips` component (dict mapping `(top, left)` to 16x16 bytearrays)
- `can_enter()` checks walkability via byte values
- Tiles sent to clients via `OutboundTile` signal on proximity
- No terrain mutation system exists yet

**Target state:**
- Tiles generate on first visit (lazy instantiation)
- Each tile tracks when it was instantiated
- Decay processor runs each tick, mutating tiles based on time and anchor distance
- Mutated tiles sync to clients

---

## Task 1: Tile Instantiation Tracking

**Files:**
- Create: `ninjamagic/terrain.py`
- Modify: `ninjamagic/component.py`
- Test: `tests/test_terrain.py`

**Step 1: Write the failing test**

```python
# tests/test_terrain.py
import pytest
from ninjamagic.terrain import get_tile_age, mark_tile_instantiated
from ninjamagic.util import Looptime

def test_tile_instantiation_tracking():
    """Tiles track when they were first instantiated."""
    map_id = 1
    now = Looptime(1000.0)

    # Before marking, age is None (not instantiated)
    assert get_tile_age(map_id, top=0, left=0, now=now) is None

    # Mark as instantiated
    mark_tile_instantiated(map_id, top=0, left=0, at=Looptime(500.0))

    # Now age is time since instantiation
    assert get_tile_age(map_id, top=0, left=0, now=now) == 500.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_terrain.py::test_tile_instantiation_tracking -v`
Expected: FAIL with "No module named 'ninjamagic.terrain'"

**Step 3: Add TileInstantiation component**

```python
# ninjamagic/component.py - add after Hostility class

@component(slots=True, kw_only=True)
class TileInstantiation:
    """Tracks when each tile was first instantiated (lazy generation).

    Key: (top, left) tile coordinates
    Value: Looptime when tile was first visited
    """
    times: dict[tuple[int, int], float] = field(default_factory=dict)
```

**Step 4: Create terrain.py with tracking functions**

```python
# ninjamagic/terrain.py
"""Terrain system: lazy instantiation and decay."""

from ninjamagic.util import Looptime, TILE_STRIDE_H, TILE_STRIDE_W
from ninjamagic.component import TileInstantiation
import esper


def _floor_to_tile(y: int, x: int) -> tuple[int, int]:
    """Floor coordinates to tile boundaries."""
    top = y // TILE_STRIDE_H * TILE_STRIDE_H
    left = x // TILE_STRIDE_W * TILE_STRIDE_W
    return top, left


def get_tile_age(map_id: int, *, top: int, left: int, now: Looptime) -> float | None:
    """Get age of tile in seconds, or None if not yet instantiated."""
    top, left = _floor_to_tile(top, left)

    if not esper.has_component(map_id, TileInstantiation):
        return None

    inst = esper.component_for_entity(map_id, TileInstantiation)
    instantiated_at = inst.times.get((top, left))

    if instantiated_at is None:
        return None

    return now - instantiated_at


def mark_tile_instantiated(map_id: int, *, top: int, left: int, at: Looptime) -> None:
    """Mark a tile as instantiated at the given time."""
    top, left = _floor_to_tile(top, left)

    if not esper.has_component(map_id, TileInstantiation):
        esper.add_component(map_id, TileInstantiation())

    inst = esper.component_for_entity(map_id, TileInstantiation)

    # Only mark if not already instantiated
    if (top, left) not in inst.times:
        inst.times[(top, left)] = at
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_terrain.py::test_tile_instantiation_tracking -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ninjamagic/terrain.py ninjamagic/component.py tests/test_terrain.py
git commit -m "feat(terrain): add tile instantiation tracking"
```

---

## Task 2: Hook Instantiation to Visibility

**Files:**
- Modify: `ninjamagic/visibility.py`
- Modify: `ninjamagic/terrain.py`
- Test: `tests/test_terrain.py`

**Step 1: Write the failing test**

```python
# tests/test_terrain.py - add this test

def test_tile_marked_on_visibility():
    """Tiles are marked as instantiated when sent to a client."""
    # This is an integration test - we'll verify the hook exists
    from ninjamagic.terrain import on_tile_sent
    from ninjamagic.util import Looptime

    map_id = 2
    now = Looptime(100.0)

    # Simulate tile being sent
    on_tile_sent(map_id, top=16, left=32, now=now)

    # Should now be tracked
    age = get_tile_age(map_id, top=16, left=32, now=Looptime(150.0))
    assert age == 50.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_terrain.py::test_tile_marked_on_visibility -v`
Expected: FAIL with "cannot import name 'on_tile_sent'"

**Step 3: Add on_tile_sent function**

```python
# ninjamagic/terrain.py - add this function

def on_tile_sent(map_id: int, *, top: int, left: int, now: Looptime) -> None:
    """Called when a tile is sent to a client. Marks it as instantiated."""
    mark_tile_instantiated(map_id, top=top, left=left, at=now)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_terrain.py::test_tile_marked_on_visibility -v`
Expected: PASS

**Step 5: Hook into visibility.py**

Find the location in `ninjamagic/visibility.py` where `OutboundTile` signals are created and add the hook. Look for the function that sends tiles to clients.

```python
# ninjamagic/visibility.py - add import at top
from ninjamagic.terrain import on_tile_sent

# In the function that creates OutboundTile signals, after creating the signal:
on_tile_sent(map_id, top=top, left=left, now=now)
```

**Step 6: Commit**

```bash
git add ninjamagic/terrain.py ninjamagic/visibility.py tests/test_terrain.py
git commit -m "feat(terrain): mark tiles instantiated on visibility"
```

---

## Task 3: Decay Rate Calculation

**Files:**
- Modify: `ninjamagic/terrain.py`
- Test: `tests/test_terrain.py`

**Step 1: Write the failing test**

```python
# tests/test_terrain.py - add these tests

def test_decay_rate_no_anchors():
    """Without anchors, decay rate is maximum."""
    from ninjamagic.terrain import get_decay_rate

    # No anchors = maximum decay (1.0)
    rate = get_decay_rate(map_id=1, y=50, x=50, anchor_positions=[])
    assert rate == 1.0


def test_decay_rate_near_anchor():
    """Near an anchor, decay rate is zero."""
    from ninjamagic.terrain import get_decay_rate, ANCHOR_STABILITY_RADIUS

    # At anchor = no decay
    rate = get_decay_rate(map_id=1, y=50, x=50, anchor_positions=[(50, 50)])
    assert rate == 0.0

    # Just inside radius = no decay
    rate = get_decay_rate(
        map_id=1, y=50, x=50 + ANCHOR_STABILITY_RADIUS - 1,
        anchor_positions=[(50, 50)]
    )
    assert rate == 0.0


def test_decay_rate_gradient():
    """Decay rate increases with distance from anchor."""
    from ninjamagic.terrain import get_decay_rate, ANCHOR_STABILITY_RADIUS

    anchor = (50, 50)

    # Just outside radius
    rate_near = get_decay_rate(
        map_id=1, y=50, x=50 + ANCHOR_STABILITY_RADIUS + 5,
        anchor_positions=[anchor]
    )

    # Far outside radius
    rate_far = get_decay_rate(
        map_id=1, y=50, x=50 + ANCHOR_STABILITY_RADIUS + 50,
        anchor_positions=[anchor]
    )

    assert 0.0 < rate_near < rate_far <= 1.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_terrain.py::test_decay_rate_no_anchors -v`
Expected: FAIL with "cannot import name 'get_decay_rate'"

**Step 3: Implement decay rate calculation**

```python
# ninjamagic/terrain.py - add constants and function

import math

# Stability radius around anchors (in cells)
ANCHOR_STABILITY_RADIUS = 24

# Maximum distance at which anchors have any effect
ANCHOR_MAX_EFFECT_DISTANCE = 100


def get_decay_rate(*, map_id: int, y: int, x: int, anchor_positions: list[tuple[int, int]]) -> float:
    """Calculate decay rate at a position based on distance from anchors.

    Returns 0.0 (no decay) to 1.0 (maximum decay).
    Inside stability radius = 0.0
    Beyond max effect distance = 1.0
    Between = linear gradient
    """
    if not anchor_positions:
        return 1.0

    # Find distance to nearest anchor
    min_distance = float('inf')
    for ay, ax in anchor_positions:
        dist = math.sqrt((y - ay) ** 2 + (x - ax) ** 2)
        min_distance = min(min_distance, dist)

    # Inside stability radius = no decay
    if min_distance <= ANCHOR_STABILITY_RADIUS:
        return 0.0

    # Beyond max effect = full decay
    if min_distance >= ANCHOR_MAX_EFFECT_DISTANCE:
        return 1.0

    # Linear gradient between radius and max effect
    gradient_range = ANCHOR_MAX_EFFECT_DISTANCE - ANCHOR_STABILITY_RADIUS
    distance_into_gradient = min_distance - ANCHOR_STABILITY_RADIUS

    return distance_into_gradient / gradient_range
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_terrain.py -k decay_rate -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add ninjamagic/terrain.py tests/test_terrain.py
git commit -m "feat(terrain): add decay rate calculation based on anchor distance"
```

---

## Task 4: Tile Mutation Definitions

**Files:**
- Modify: `ninjamagic/terrain.py`
- Test: `tests/test_terrain.py`

**Step 1: Write the failing test**

```python
# tests/test_terrain.py - add this test

def test_tile_decay_mapping():
    """Tiles have defined decay paths."""
    from ninjamagic.terrain import get_decay_target, TILE_FLOOR, TILE_OVERGROWN, TILE_WALL

    # Floor decays to overgrown
    assert get_decay_target(TILE_FLOOR) == TILE_OVERGROWN

    # Walls don't decay
    assert get_decay_target(TILE_WALL) is None

    # Overgrown decays further (or stops)
    target = get_decay_target(TILE_OVERGROWN)
    assert target is None or target != TILE_OVERGROWN  # Either stops or changes
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_terrain.py::test_tile_decay_mapping -v`
Expected: FAIL with "cannot import name 'get_decay_target'"

**Step 3: Define tile constants and decay mappings**

```python
# ninjamagic/terrain.py - add tile definitions

# Tile type constants (must match ChipSet definitions)
TILE_VOID = 0
TILE_FLOOR = 1
TILE_WALL = 2
TILE_GRASS = 3
TILE_OVERGROWN = 4  # New: decayed floor
TILE_DENSE_OVERGROWN = 5  # New: heavily decayed, difficult terrain

# Decay mappings: what each tile becomes when decayed
DECAY_MAP: dict[int, int | None] = {
    TILE_FLOOR: TILE_OVERGROWN,
    TILE_GRASS: TILE_OVERGROWN,
    TILE_OVERGROWN: TILE_DENSE_OVERGROWN,
    TILE_DENSE_OVERGROWN: None,  # Terminal state
    TILE_WALL: None,  # Doesn't decay
    TILE_VOID: None,  # Doesn't decay
}

# Time in seconds for one decay step at maximum decay rate
DECAY_INTERVAL = 300.0  # 5 minutes


def get_decay_target(tile_id: int) -> int | None:
    """Get what a tile decays into, or None if it doesn't decay."""
    return DECAY_MAP.get(tile_id)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_terrain.py::test_tile_decay_mapping -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/terrain.py tests/test_terrain.py
git commit -m "feat(terrain): define tile decay mappings"
```

---

## Task 5: Decay Processor

**Files:**
- Modify: `ninjamagic/terrain.py`
- Modify: `ninjamagic/bus.py`
- Test: `tests/test_terrain.py`

**Step 1: Write the failing test**

```python
# tests/test_terrain.py - add this test

def test_decay_processor_mutates_tiles():
    """Decay processor mutates old tiles outside anchor radius."""
    from ninjamagic.terrain import (
        process_decay, mark_tile_instantiated,
        TILE_FLOOR, TILE_OVERGROWN, DECAY_INTERVAL
    )
    from ninjamagic.util import Looptime
    import esper
    from ninjamagic.component import Chips, TileInstantiation

    # Setup: create a map with a floor tile
    esper.clear_database()
    map_id = esper.create_entity()

    # Create a 16x16 tile of floor
    tile_data = bytearray([TILE_FLOOR] * 256)
    esper.add_component(map_id, Chips({(0, 0): tile_data}))
    esper.add_component(map_id, TileInstantiation())

    # Mark tile as instantiated long ago
    old_time = Looptime(0.0)
    mark_tile_instantiated(map_id, top=0, left=0, at=old_time)

    # Process decay at a time when decay should occur
    # (DECAY_INTERVAL seconds later, no anchors = full decay rate)
    now = Looptime(DECAY_INTERVAL + 1.0)
    process_decay(now=now, anchor_positions=[])

    # Tile should have decayed
    chips = esper.component_for_entity(map_id, Chips)
    assert chips[(0, 0)][0] == TILE_OVERGROWN
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_terrain.py::test_decay_processor_mutates_tiles -v`
Expected: FAIL with "cannot import name 'process_decay'"

**Step 3: Add TileMutated signal to bus.py**

```python
# ninjamagic/bus.py - add this signal class

@frozen
class TileMutated(Signal):
    """A terrain tile has changed."""
    map_id: int
    top: int
    left: int
    y: int  # Cell within tile
    x: int  # Cell within tile
    old_tile: int
    new_tile: int
```

**Step 4: Implement decay processor**

```python
# ninjamagic/terrain.py - add this function

from ninjamagic import bus
from ninjamagic.component import Chips, TileInstantiation


def process_decay(*, now: Looptime, anchor_positions: list[tuple[int, int]]) -> None:
    """Process terrain decay for all instantiated tiles."""

    for map_id, (chips, inst) in esper.get_components(Chips, TileInstantiation):
        tiles_to_check = list(inst.times.keys())

        for (top, left) in tiles_to_check:
            tile_data = chips.get((top, left))
            if tile_data is None:
                continue

            age = get_tile_age(map_id, top=top, left=left, now=now)
            if age is None:
                continue

            # Check each cell in the tile
            for idx in range(len(tile_data)):
                cell_y = top + idx // TILE_STRIDE_W
                cell_x = left + idx % TILE_STRIDE_W

                # Get decay rate for this cell
                decay_rate = get_decay_rate(
                    map_id=map_id, y=cell_y, x=cell_x,
                    anchor_positions=anchor_positions
                )

                if decay_rate == 0.0:
                    continue

                # Calculate effective decay time
                effective_age = age * decay_rate

                # Check if enough time has passed for decay
                current_tile = tile_data[idx]
                decay_target = get_decay_target(current_tile)

                if decay_target is None:
                    continue

                if effective_age >= DECAY_INTERVAL:
                    # Mutate the tile
                    old_tile = tile_data[idx]
                    tile_data[idx] = decay_target

                    # Signal the change
                    bus.pulse(bus.TileMutated(
                        map_id=map_id,
                        top=top, left=left,
                        y=idx // TILE_STRIDE_W,
                        x=idx % TILE_STRIDE_W,
                        old_tile=old_tile,
                        new_tile=decay_target,
                    ))

            # Reset instantiation time for decayed tiles (so decay continues)
            inst.times[(top, left)] = now
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_terrain.py::test_decay_processor_mutates_tiles -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ninjamagic/terrain.py ninjamagic/bus.py tests/test_terrain.py
git commit -m "feat(terrain): add decay processor"
```

---

## Task 6: Integrate Decay into Game Loop

**Files:**
- Modify: `ninjamagic/state.py`
- Modify: `ninjamagic/terrain.py`

**Step 1: Create a wrapper that gathers anchor positions**

```python
# ninjamagic/terrain.py - add this function

from ninjamagic.component import Anchor, Transform


def process(now: Looptime) -> None:
    """Main terrain processor - call from game loop."""
    # Gather all anchor positions
    anchor_positions: list[tuple[int, int]] = []

    for eid, (anchor, transform) in esper.get_components(Anchor, Transform):
        anchor_positions.append((transform.y, transform.x))

    # Run decay
    process_decay(now=now, anchor_positions=anchor_positions)
```

**Step 2: Add to game loop in state.py**

Find the `step()` method in `ninjamagic/state.py` and add terrain processing. It should run after visibility but before outbox, so tile changes are sent to clients.

```python
# ninjamagic/state.py - add import
from ninjamagic import terrain

# In State.step(), add after visibility processing:
terrain.process(now=self.now)
```

**Step 3: Manual test**

Run the server and verify:
1. Walk around to instantiate tiles
2. Wait 5+ minutes (or temporarily reduce DECAY_INTERVAL for testing)
3. Tiles outside anchor radius should decay

**Step 4: Commit**

```bash
git add ninjamagic/terrain.py ninjamagic/state.py
git commit -m "feat(terrain): integrate decay into game loop"
```

---

## Task 7: Sync Mutated Tiles to Clients

**Files:**
- Modify: `ninjamagic/visibility.py`
- Test: Manual testing

**Step 1: Handle TileMutated signals**

```python
# ninjamagic/visibility.py - add handler for TileMutated

# In the process() function, add handling for TileMutated signals:

for sig in bus.receive(bus.TileMutated):
    # Resend the affected tile to all nearby players
    for eid, (conn, transform) in esper.get_components(Conn, Transform):
        if transform.map_id != sig.map_id:
            continue

        # Check if player is close enough to see this tile
        dy = abs(transform.y - sig.top)
        dx = abs(transform.x - sig.left)

        if dy <= VIEW_STRIDE_H + TILE_STRIDE_H and dx <= VIEW_STRIDE_W + TILE_STRIDE_W:
            # Mark tile as needing resend
            sent_tiles = _get_sent_tiles(conn)
            sent_tiles.discard((sig.map_id, sig.top, sig.left))

            # Queue tile for sending
            bus.pulse(bus.OutboundTile(
                dest=eid,
                map_id=sig.map_id,
                top=sig.top,
                left=sig.left,
            ))
```

**Step 2: Manual test**

Run the server with reduced DECAY_INTERVAL and verify tile changes are visible to players.

**Step 3: Commit**

```bash
git add ninjamagic/visibility.py
git commit -m "feat(terrain): sync mutated tiles to clients"
```

---

## Task 8: Add Overgrown Tile Visuals

**Files:**
- Modify: `ninjamagic/world/state.py` (ChipSet definitions)

**Step 1: Add new tile visuals to ChipSet**

Find where ChipSet is defined (likely in map creation) and add entries for new tile types:

```python
# Add to ChipSet definitions
(TILE_OVERGROWN, map_id, ord("\""), 0.35, 0.6, 0.5, 1.0),  # Green-ish grass
(TILE_DENSE_OVERGROWN, map_id, ord("%"), 0.30, 0.7, 0.4, 1.0),  # Darker, denser
```

**Step 2: Update can_enter() if needed**

If overgrown tiles should have movement penalties, update the walkability checks:

```python
# ninjamagic/world/state.py - modify can_enter()
# TILE_OVERGROWN (4) should still be walkable
# TILE_DENSE_OVERGROWN (5) could be walkable but with movement cost
WALKABLE_TILES = {TILE_FLOOR, TILE_GRASS, TILE_OVERGROWN, TILE_DENSE_OVERGROWN}
```

**Step 3: Commit**

```bash
git add ninjamagic/world/state.py
git commit -m "feat(terrain): add overgrown tile visuals"
```

---

## Summary

After completing all tasks, you will have:

1. **Tile instantiation tracking** - tiles know when they were first seen
2. **Automatic instantiation** - tiles marked when sent to clients
3. **Decay rate calculation** - based on distance from anchors
4. **Decay mappings** - floor → overgrown → dense overgrown
5. **Decay processor** - runs each tick, mutates old tiles
6. **Game loop integration** - decay runs as part of normal processing
7. **Client sync** - mutated tiles sent to nearby players
8. **Visual feedback** - new tile types with distinct glyphs

**Next plan:** Anchor System (stability radius, creation, maintenance)
