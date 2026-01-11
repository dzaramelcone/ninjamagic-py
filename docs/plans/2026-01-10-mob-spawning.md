# Mob Spawning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement mob spawning from unlit tiles and basic AI pathfinding toward anchors - the darkness made manifest.

**Architecture:** Mobs spawn from tiles outside anchor stability radii. They have a simple AI that paths toward the nearest anchor. Spawn rate scales with time of day (peaks at night). This creates the "darkness reaching for your light" mechanic.

**Tech Stack:** Python, esper ECS, signal bus, A* pathfinding

---

## Background

**Current state:**
- One "wanderer" entity exists as a placeholder NPC
- No AI or behavior system
- Combat system exists and works between any entities
- No spawning logic

**Target state:**
- Mobs spawn from darkness (outside anchor radii)
- Simple pathfinding AI moves mobs toward anchors
- Spawn rate controlled by time of day
- Mobs attack players in their path

---

## Task 1: Mob Component

**Files:**
- Modify: `ninjamagic/component.py`
- Test: `tests/test_mob.py`

**Step 1: Write the failing test**

```python
# tests/test_mob.py
import pytest
from ninjamagic.component import Mob, MobType

def test_mob_component():
    """Mobs have type and behavior properties."""
    mob = Mob(mob_type=MobType.SWARM, aggro_range=8)

    assert mob.mob_type == MobType.SWARM
    assert mob.aggro_range == 8


def test_mob_defaults():
    """Mobs have sensible defaults."""
    mob = Mob()

    assert mob.mob_type == MobType.SWARM
    assert mob.aggro_range == 6
    assert mob.target is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mob.py::test_mob_component -v`
Expected: FAIL with "cannot import name 'Mob'"

**Step 3: Add Mob component and MobType enum**

```python
# ninjamagic/component.py - add these

from enum import Enum

class MobType(Enum):
    """Types of mobs with different behaviors."""
    SWARM = "swarm"      # Weak, numerous
    PACK = "pack"        # Coordinated group
    DEATH_KNIGHT = "death_knight"  # Strong 1v1
    BOSS = "boss"        # Special encounter


@component(slots=True, kw_only=True)
class Mob:
    """Marks an entity as a hostile mob with AI behavior.

    Attributes:
        mob_type: The mob phenotype (affects behavior).
        aggro_range: Distance at which mob notices players.
        target: Current target entity (anchor or player).
    """
    mob_type: MobType = MobType.SWARM
    aggro_range: int = 6
    target: int | None = None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mob.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/component.py tests/test_mob.py
git commit -m "feat(mob): add Mob component and MobType enum"
```

---

## Task 2: Spawn Point Selection

**Files:**
- Create: `ninjamagic/spawn.py`
- Test: `tests/test_spawn.py`

**Step 1: Write the failing test**

```python
# tests/test_spawn.py
import pytest
from ninjamagic.spawn import find_spawn_point

def test_find_spawn_point_avoids_anchors():
    """Spawn points are outside anchor radii."""
    # Anchor at (50, 50) with radius 24
    anchors = [(50, 50, 24.0)]

    # Should find a point outside the radius
    point = find_spawn_point(
        map_id=1,
        anchors=anchors,
        min_distance=30,
        max_distance=50,
        walkable_check=lambda y, x: True,  # All walkable for test
    )

    assert point is not None
    y, x = point

    # Verify it's outside anchor radius
    import math
    dist = math.sqrt((y - 50) ** 2 + (x - 50) ** 2)
    assert dist >= 24


def test_find_spawn_point_respects_walkable():
    """Spawn points must be on walkable tiles."""
    anchors = [(50, 50, 24.0)]

    # Nothing walkable = no spawn point
    point = find_spawn_point(
        map_id=1,
        anchors=anchors,
        min_distance=30,
        max_distance=50,
        walkable_check=lambda y, x: False,
    )

    assert point is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spawn.py::test_find_spawn_point_avoids_anchors -v`
Expected: FAIL with "No module named 'ninjamagic.spawn'"

**Step 3: Create spawn.py with spawn point selection**

```python
# ninjamagic/spawn.py
"""Mob spawning system: spawn from darkness, path toward light."""

import math
import random
from typing import Callable


def find_spawn_point(
    *,
    map_id: int,
    anchors: list[tuple[int, int, float]],  # (y, x, radius)
    min_distance: int,
    max_distance: int,
    walkable_check: Callable[[int, int], bool],
    max_attempts: int = 50,
) -> tuple[int, int] | None:
    """Find a valid spawn point outside all anchor radii.

    Args:
        map_id: The map to spawn on.
        anchors: List of (y, x, radius) tuples for each anchor.
        min_distance: Minimum distance from any anchor.
        max_distance: Maximum distance from nearest anchor.
        walkable_check: Function that returns True if (y, x) is walkable.
        max_attempts: Number of random attempts before giving up.

    Returns:
        (y, x) tuple if found, None if no valid point exists.
    """
    if not anchors:
        return None  # No anchors = nowhere to spawn toward

    for _ in range(max_attempts):
        # Pick a random anchor to spawn near
        anchor_y, anchor_x, radius = random.choice(anchors)

        # Pick random angle and distance
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(
            max(min_distance, radius + 1),  # At least outside radius
            max_distance
        )

        # Calculate point
        y = int(anchor_y + distance * math.sin(angle))
        x = int(anchor_x + distance * math.cos(angle))

        # Check if outside ALL anchor radii
        in_any_radius = False
        for ay, ax, ar in anchors:
            dist_to_anchor = math.sqrt((y - ay) ** 2 + (x - ax) ** 2)
            if dist_to_anchor <= ar:
                in_any_radius = True
                break

        if in_any_radius:
            continue

        # Check if walkable
        if not walkable_check(y, x):
            continue

        return (y, x)

    return None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_spawn.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/spawn.py tests/test_spawn.py
git commit -m "feat(spawn): add spawn point selection outside anchor radii"
```

---

## Task 3: Mob Factory

**Files:**
- Modify: `ninjamagic/spawn.py`
- Test: `tests/test_spawn.py`

**Step 1: Write the failing test**

```python
# tests/test_spawn.py - add this test

def test_create_mob():
    """Create a mob entity with all required components."""
    import esper
    from ninjamagic.spawn import create_mob
    from ninjamagic.component import (
        Mob, MobType, Transform, Health, Noun, Glyph, Stance, Skills
    )

    esper.clear_database()

    eid = create_mob(
        mob_type=MobType.SWARM,
        map_id=1,
        y=10,
        x=20,
        name="goblin",
    )

    # Verify all components
    assert esper.has_component(eid, Mob)
    assert esper.has_component(eid, Transform)
    assert esper.has_component(eid, Health)
    assert esper.has_component(eid, Noun)
    assert esper.has_component(eid, Stance)
    assert esper.has_component(eid, Skills)

    mob = esper.component_for_entity(eid, Mob)
    assert mob.mob_type == MobType.SWARM

    transform = esper.component_for_entity(eid, Transform)
    assert transform.map_id == 1
    assert transform.y == 10
    assert transform.x == 20
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spawn.py::test_create_mob -v`
Expected: FAIL with "cannot import name 'create_mob'"

**Step 3: Implement mob factory**

```python
# ninjamagic/spawn.py - add imports and function

import esper
from ninjamagic.component import (
    Mob, MobType, Transform, Health, Noun, Stance, Skills, Stats, Glyph, Pronouns
)


# Mob type configurations
MOB_CONFIGS = {
    MobType.SWARM: {
        "glyph": "g",
        "hue": 0.33,
        "health": 25.0,
        "aggro_range": 4,
    },
    MobType.PACK: {
        "glyph": "w",
        "hue": 0.08,
        "health": 50.0,
        "aggro_range": 6,
    },
    MobType.DEATH_KNIGHT: {
        "glyph": "D",
        "hue": 0.0,
        "health": 100.0,
        "aggro_range": 8,
    },
    MobType.BOSS: {
        "glyph": "B",
        "hue": 0.75,
        "health": 200.0,
        "aggro_range": 12,
    },
}


def create_mob(
    *,
    mob_type: MobType,
    map_id: int,
    y: int,
    x: int,
    name: str,
) -> int:
    """Create a mob entity with all required components.

    Returns the entity ID.
    """
    config = MOB_CONFIGS.get(mob_type, MOB_CONFIGS[MobType.SWARM])

    eid = esper.create_entity()

    esper.add_component(eid, Transform(map_id=map_id, y=y, x=x))
    esper.add_component(eid, Mob(
        mob_type=mob_type,
        aggro_range=config["aggro_range"],
    ))
    esper.add_component(eid, Health(cur=config["health"], stress=0.0))
    esper.add_component(eid, Noun(value=name, pronoun=Pronouns.IT))
    esper.add_component(eid, Stance())
    esper.add_component(eid, Skills())
    esper.add_component(eid, Stats())
    esper.add_component(eid, (config["glyph"], config["hue"], 0.6, 0.7), Glyph)

    return eid
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spawn.py::test_create_mob -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/spawn.py tests/test_spawn.py
git commit -m "feat(spawn): add mob factory function"
```

---

## Task 4: Simple Pathfinding

**Files:**
- Create: `ninjamagic/pathfind.py`
- Test: `tests/test_pathfind.py`

**Step 1: Write the failing test**

```python
# tests/test_pathfind.py
import pytest
from ninjamagic.pathfind import find_path, get_next_step

def test_find_path_straight_line():
    """Find path in a straight line."""
    # Simple grid where everything is walkable
    walkable = lambda y, x: True

    path = find_path(
        start=(0, 0),
        goal=(0, 5),
        walkable_check=walkable,
        max_distance=10,
    )

    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (0, 5)


def test_get_next_step_toward_goal():
    """Get the next step toward a goal."""
    walkable = lambda y, x: True

    next_step = get_next_step(
        current=(5, 5),
        goal=(5, 10),
        walkable_check=walkable,
    )

    assert next_step is not None
    y, x = next_step
    # Should move toward goal (east)
    assert x > 5 or y != 5  # Moved somehow


def test_get_next_step_blocked():
    """Returns None if no path exists."""
    # Nothing walkable except current position
    walkable = lambda y, x: (y, x) == (5, 5)

    next_step = get_next_step(
        current=(5, 5),
        goal=(5, 10),
        walkable_check=walkable,
    )

    assert next_step is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pathfind.py::test_find_path_straight_line -v`
Expected: FAIL with "No module named 'ninjamagic.pathfind'"

**Step 3: Implement simple A* pathfinding**

```python
# ninjamagic/pathfind.py
"""Simple A* pathfinding for mob movement."""

import heapq
import math
from typing import Callable


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
    """Get 8-directional neighbors."""
    y, x = pos
    return [
        (y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1),  # Cardinals
        (y - 1, x - 1), (y - 1, x + 1), (y + 1, x - 1), (y + 1, x + 1),  # Diagonals
    ]


def find_path(
    *,
    start: tuple[int, int],
    goal: tuple[int, int],
    walkable_check: Callable[[int, int], bool],
    max_distance: int = 100,
) -> list[tuple[int, int]] | None:
    """Find a path from start to goal using A*.

    Returns list of (y, x) positions, or None if no path exists.
    """
    if start == goal:
        return [start]

    # A* implementation
    open_set = [(0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in _neighbors(current):
            # Check bounds (simple check)
            if abs(neighbor[0] - start[0]) > max_distance:
                continue
            if abs(neighbor[1] - start[1]) > max_distance:
                continue

            if not walkable_check(neighbor[0], neighbor[1]):
                continue

            # Diagonal moves cost more
            dy = abs(neighbor[0] - current[0])
            dx = abs(neighbor[1] - current[1])
            move_cost = 1.414 if (dy + dx) == 2 else 1.0

            tentative_g = g_score[current] + move_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + _heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))

    return None


def get_next_step(
    *,
    current: tuple[int, int],
    goal: tuple[int, int],
    walkable_check: Callable[[int, int], bool],
) -> tuple[int, int] | None:
    """Get the next step toward a goal.

    Returns the next (y, x) position, or None if blocked.
    """
    path = find_path(
        start=current,
        goal=goal,
        walkable_check=walkable_check,
        max_distance=50,
    )

    if path is None or len(path) < 2:
        return None

    return path[1]
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pathfind.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/pathfind.py tests/test_pathfind.py
git commit -m "feat(pathfind): add simple A* pathfinding"
```

---

## Task 5: Mob AI Processor

**Files:**
- Create: `ninjamagic/mob_ai.py`
- Test: `tests/test_mob_ai.py`

**Step 1: Write the failing test**

```python
# tests/test_mob_ai.py
import pytest
import esper
from ninjamagic.mob_ai import process_mob_ai
from ninjamagic.component import Mob, MobType, Transform, Anchor
from ninjamagic import bus

def test_mob_moves_toward_anchor():
    """Mobs path toward the nearest anchor."""
    esper.clear_database()

    # Create a map
    map_id = esper.create_entity()

    # Create an anchor at (50, 50)
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=50, x=50))
    esper.add_component(anchor_eid, Anchor())

    # Create a mob at (50, 60) - 10 tiles away
    mob_eid = esper.create_entity()
    esper.add_component(mob_eid, Transform(map_id=map_id, y=50, x=60))
    esper.add_component(mob_eid, Mob(mob_type=MobType.SWARM))

    # Process AI
    walkable = lambda y, x: True
    process_mob_ai(walkable_check=walkable)

    # Check that a move signal was emitted
    move_signals = list(bus.receive(bus.MoveCompass))
    assert len(move_signals) > 0

    # The mob should be moving west (toward anchor)
    sig = move_signals[0]
    assert sig.source == mob_eid

    bus.clear()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mob_ai.py::test_mob_moves_toward_anchor -v`
Expected: FAIL with "No module named 'ninjamagic.mob_ai'"

**Step 3: Implement mob AI processor**

```python
# ninjamagic/mob_ai.py
"""Mob AI: simple behavior that paths toward anchors."""

import esper
from typing import Callable
from ninjamagic import bus
from ninjamagic.component import Mob, Transform, Anchor
from ninjamagic.pathfind import get_next_step


def _get_nearest_anchor(map_id: int, y: int, x: int) -> tuple[int, int] | None:
    """Find the position of the nearest anchor on this map."""
    nearest = None
    nearest_dist = float('inf')

    for eid, (anchor, transform) in esper.get_components(Anchor, Transform):
        if transform.map_id != map_id:
            continue

        dist = abs(transform.y - y) + abs(transform.x - x)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = (transform.y, transform.x)

    return nearest


def _direction_to_compass(dy: int, dx: int) -> str:
    """Convert delta to compass direction."""
    if dy < 0 and dx == 0:
        return "n"
    if dy > 0 and dx == 0:
        return "s"
    if dy == 0 and dx < 0:
        return "w"
    if dy == 0 and dx > 0:
        return "e"
    if dy < 0 and dx < 0:
        return "nw"
    if dy < 0 and dx > 0:
        return "ne"
    if dy > 0 and dx < 0:
        return "sw"
    if dy > 0 and dx > 0:
        return "se"
    return "n"  # Fallback


def process_mob_ai(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process AI for all mobs.

    Mobs path toward the nearest anchor.
    """
    for eid, (mob, transform) in esper.get_components(Mob, Transform):
        # Find nearest anchor
        target = _get_nearest_anchor(transform.map_id, transform.y, transform.x)
        if target is None:
            continue

        # Already at target?
        if (transform.y, transform.x) == target:
            continue

        # Get next step toward target
        next_pos = get_next_step(
            current=(transform.y, transform.x),
            goal=target,
            walkable_check=walkable_check,
        )

        if next_pos is None:
            continue

        # Calculate direction
        dy = next_pos[0] - transform.y
        dx = next_pos[1] - transform.x
        direction = _direction_to_compass(dy, dx)

        # Emit move signal
        bus.pulse(bus.MoveCompass(source=eid, direction=direction))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mob_ai.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/mob_ai.py tests/test_mob_ai.py
git commit -m "feat(mob_ai): add basic mob AI that paths toward anchors"
```

---

## Task 6: Spawn Processor

**Files:**
- Modify: `ninjamagic/spawn.py`
- Test: `tests/test_spawn.py`

**Step 1: Write the failing test**

```python
# tests/test_spawn.py - add this test

def test_spawn_processor():
    """Spawn processor creates mobs over time."""
    import esper
    from ninjamagic.spawn import process_spawning, SpawnConfig
    from ninjamagic.component import Mob, Transform, Anchor
    from ninjamagic.anchor import get_anchor_positions_with_radii

    esper.clear_database()

    # Create a map
    map_id = esper.create_entity()

    # Create an anchor
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=50, x=50))
    esper.add_component(anchor_eid, Anchor(strength=1.0, fuel=100.0))

    # Configure spawning
    config = SpawnConfig(
        spawn_rate=1.0,  # 1 mob per second
        max_mobs=10,
        min_distance=30,
        max_distance=50,
    )

    # Process spawning for 2 seconds
    walkable = lambda y, x: True
    process_spawning(
        map_id=map_id,
        delta_seconds=2.0,
        config=config,
        walkable_check=walkable,
    )

    # Should have spawned some mobs
    mob_count = len(list(esper.get_component(Mob)))
    assert mob_count >= 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spawn.py::test_spawn_processor -v`
Expected: FAIL with "cannot import name 'process_spawning'"

**Step 3: Implement spawn processor**

```python
# ninjamagic/spawn.py - add these

from dataclasses import dataclass
from ninjamagic.anchor import get_anchor_positions_with_radii


@dataclass
class SpawnConfig:
    """Configuration for mob spawning."""
    spawn_rate: float = 0.1  # Mobs per second (base rate)
    max_mobs: int = 20  # Maximum mobs on map
    min_distance: int = 30  # Minimum distance from anchors
    max_distance: int = 60  # Maximum distance from anchors


# Track spawn accumulator per map
_spawn_accumulators: dict[int, float] = {}


def process_spawning(
    *,
    map_id: int,
    delta_seconds: float,
    config: SpawnConfig,
    walkable_check: Callable[[int, int], bool],
) -> list[int]:
    """Process mob spawning for a map.

    Returns list of newly spawned mob entity IDs.
    """
    spawned = []

    # Get anchor positions
    anchors = get_anchor_positions_with_radii()
    map_anchors = [(y, x, r) for y, x, r in anchors]  # Filter by map_id if needed

    if not map_anchors:
        return spawned  # No anchors = no spawning

    # Count current mobs
    current_mobs = sum(1 for _ in esper.get_component(Mob))
    if current_mobs >= config.max_mobs:
        return spawned

    # Accumulate spawn progress
    if map_id not in _spawn_accumulators:
        _spawn_accumulators[map_id] = 0.0

    _spawn_accumulators[map_id] += delta_seconds * config.spawn_rate

    # Spawn mobs
    while _spawn_accumulators[map_id] >= 1.0 and current_mobs < config.max_mobs:
        _spawn_accumulators[map_id] -= 1.0

        # Find spawn point
        point = find_spawn_point(
            map_id=map_id,
            anchors=map_anchors,
            min_distance=config.min_distance,
            max_distance=config.max_distance,
            walkable_check=walkable_check,
        )

        if point is None:
            continue

        y, x = point

        # Create mob
        eid = create_mob(
            mob_type=MobType.SWARM,
            map_id=map_id,
            y=y,
            x=x,
            name="goblin",
        )

        spawned.append(eid)
        current_mobs += 1

    return spawned
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spawn.py::test_spawn_processor -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/spawn.py tests/test_spawn.py
git commit -m "feat(spawn): add spawn processor"
```

---

## Task 7: Integrate into Game Loop

**Files:**
- Modify: `ninjamagic/state.py`

**Step 1: Add mob AI and spawning to game loop**

```python
# ninjamagic/state.py - add imports
from ninjamagic import mob_ai, spawn
from ninjamagic.world.state import can_enter

# In State.step(), add after anchor processing:

# Mob AI (runs every N ticks to avoid too frequent pathfinding)
if self.tick % 60 == 0:  # Every 0.25 seconds at 240 TPS
    mob_ai.process_mob_ai(walkable_check=lambda y, x: can_enter(map_id=..., y=y, x=x))

# Mob spawning
spawn_config = spawn.SpawnConfig(spawn_rate=0.1, max_mobs=20)
spawn.process_spawning(
    map_id=...,  # Get from current map
    delta_seconds=self.delta,
    config=spawn_config,
    walkable_check=lambda y, x: can_enter(map_id=..., y=y, x=x),
)
```

Note: The exact integration depends on how map_id is tracked. May need to iterate over all active maps.

**Step 2: Manual test**

Run the server and verify:
1. Mobs spawn outside the bonfire radius
2. Mobs move toward the bonfire

**Step 3: Commit**

```bash
git add ninjamagic/state.py
git commit -m "feat(spawn): integrate mob AI and spawning into game loop"
```

---

## Task 8: Mob Despawning

**Files:**
- Modify: `ninjamagic/spawn.py`

**Step 1: Add despawn logic**

Mobs should despawn when:
- They reach the anchor (for now, later they'll attack)
- They've been alive too long without engaging

```python
# ninjamagic/spawn.py - add despawn function

def process_despawning() -> list[int]:
    """Remove mobs that should despawn.

    Returns list of despawned entity IDs.
    """
    despawned = []

    for eid, (mob, transform) in esper.get_components(Mob, Transform):
        # Check if at an anchor
        for anchor_eid, (anchor, anchor_transform) in esper.get_components(Anchor, Transform):
            if anchor_transform.map_id != transform.map_id:
                continue

            dist = abs(transform.y - anchor_transform.y) + abs(transform.x - anchor_transform.x)
            if dist <= 1:
                # At anchor - despawn (later: attack instead)
                esper.delete_entity(eid)
                despawned.append(eid)
                break

    return despawned
```

**Step 2: Add to game loop**

```python
# In State.step():
spawn.process_despawning()
```

**Step 3: Commit**

```bash
git add ninjamagic/spawn.py ninjamagic/state.py
git commit -m "feat(spawn): add mob despawning at anchors"
```

---

## Summary

After completing all tasks, you will have:

1. **Mob component** - marks entities as hostile mobs with type and aggro range
2. **Spawn point selection** - finds valid points outside anchor radii
3. **Mob factory** - creates complete mob entities with all components
4. **A* pathfinding** - finds paths through the terrain
5. **Mob AI** - moves mobs toward nearest anchor
6. **Spawn processor** - creates mobs over time based on config
7. **Game loop integration** - AI and spawning run each tick
8. **Despawning** - mobs removed when reaching anchors

**Dependencies:** Requires Anchor System plan (for `get_anchor_positions_with_radii`).

**Next plan:** Wave System (time-based spawn rate scaling)
