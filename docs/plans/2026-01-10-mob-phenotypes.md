# Mob Phenotypes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement distinct mob behaviors for each phenotype - swarm, pack, death knight, and special encounters.

**Architecture:** Each MobType has a behavior module that defines how the mob acts (movement, targeting, attack patterns). The mob AI processor dispatches to the appropriate behavior based on MobType. This creates variety in combat encounters.

**Tech Stack:** Python, esper ECS, signal bus

---

## Background

**Current state (after Mob Spawning plan):**
- MobType enum: SWARM, PACK, DEATH_KNIGHT, BOSS
- All mobs use same basic AI (path toward anchor)
- MOB_CONFIGS defines glyph/health/aggro per type

**Target state:**
- Swarm: Weak, fast, attack in numbers
- Pack: Coordinated, mixed roles (some attack, some flank)
- Death Knight: Strong 1v1, matches player strength
- Special Encounter: Boss with add spawning
- Invader: Q1 stretch (agentic AI)

---

## Task 1: Behavior Component

**Files:**
- Modify: `ninjamagic/component.py`
- Test: `tests/test_mob.py`

**Step 1: Write the failing test**

```python
# tests/test_mob.py - add this test

def test_mob_behavior_component():
    """Mobs have behavior state."""
    from ninjamagic.component import MobBehavior, BehaviorState

    behavior = MobBehavior(
        state=BehaviorState.IDLE,
        target_entity=None,
        cooldown=0.0,
    )

    assert behavior.state == BehaviorState.IDLE
    assert behavior.target_entity is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mob.py::test_mob_behavior_component -v`
Expected: FAIL with "cannot import name 'MobBehavior'"

**Step 3: Add MobBehavior component**

```python
# ninjamagic/component.py - add these

class BehaviorState(Enum):
    """Mob behavior states."""
    IDLE = "idle"          # Not doing anything
    PATHING = "pathing"    # Moving toward target
    ENGAGING = "engaging"  # In combat
    FLANKING = "flanking"  # Circling around (pack behavior)
    SUMMONING = "summoning"  # Spawning adds (boss behavior)
    RETREATING = "retreating"  # Backing off


@component(slots=True, kw_only=True)
class MobBehavior:
    """Mob AI behavior state.

    Attributes:
        state: Current behavior state.
        target_entity: Entity being targeted (player or anchor).
        cooldown: Time until next action.
        pack_leader: For pack mobs, the leader entity.
    """
    state: BehaviorState = BehaviorState.IDLE
    target_entity: int | None = None
    cooldown: float = 0.0
    pack_leader: int | None = None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mob.py::test_mob_behavior_component -v`
Expected: PASS

**Step 5: Update mob factory to add MobBehavior**

```python
# ninjamagic/spawn.py - in create_mob, add:
esper.add_component(eid, MobBehavior())
```

**Step 6: Commit**

```bash
git add ninjamagic/component.py ninjamagic/spawn.py tests/test_mob.py
git commit -m "feat(mob): add MobBehavior component"
```

---

## Task 2: Swarm Behavior

**Files:**
- Create: `ninjamagic/behavior/swarm.py`
- Test: `tests/test_behavior.py`

**Step 1: Write the failing test**

```python
# tests/test_behavior.py
import pytest
import esper
from ninjamagic.behavior.swarm import process_swarm
from ninjamagic.component import (
    Mob, MobType, MobBehavior, BehaviorState, Transform, Health
)
from ninjamagic import bus

def test_swarm_targets_nearest_player():
    """Swarm mobs target the nearest player."""
    esper.clear_database()

    map_id = esper.create_entity()

    # Create a player
    from ninjamagic.component import Conn
    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player, Health())
    esper.add_component(player, Conn())  # Mark as player

    # Create a swarm mob
    mob = esper.create_entity()
    esper.add_component(mob, Transform(map_id=map_id, y=15, x=15))
    esper.add_component(mob, Mob(mob_type=MobType.SWARM, aggro_range=10))
    esper.add_component(mob, MobBehavior())
    esper.add_component(mob, Health())

    # Process swarm behavior
    walkable = lambda y, x: True
    process_swarm(walkable_check=walkable)

    # Mob should target player
    behavior = esper.component_for_entity(mob, MobBehavior)
    assert behavior.target_entity == player
    assert behavior.state == BehaviorState.PATHING


def test_swarm_attacks_when_adjacent():
    """Swarm mobs attack when next to target."""
    esper.clear_database()

    map_id = esper.create_entity()

    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player, Health())
    esper.add_component(player, Conn())

    mob = esper.create_entity()
    esper.add_component(mob, Transform(map_id=map_id, y=10, x=11))  # Adjacent
    esper.add_component(mob, Mob(mob_type=MobType.SWARM))
    esper.add_component(mob, MobBehavior(target_entity=player))
    esper.add_component(mob, Health())

    walkable = lambda y, x: True
    process_swarm(walkable_check=walkable)

    # Should emit attack signal
    melee_signals = list(bus.receive(bus.Melee))
    assert len(melee_signals) > 0
    assert melee_signals[0].source == mob
    assert melee_signals[0].target == player

    bus.clear()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_behavior.py::test_swarm_targets_nearest_player -v`
Expected: FAIL with "No module named 'ninjamagic.behavior'"

**Step 3: Create behavior package and swarm module**

```bash
mkdir -p ninjamagic/behavior
touch ninjamagic/behavior/__init__.py
```

```python
# ninjamagic/behavior/swarm.py
"""Swarm mob behavior: weak, fast, attacks in numbers."""

import esper
from typing import Callable
from ninjamagic import bus
from ninjamagic.component import (
    Mob, MobType, MobBehavior, BehaviorState, Transform, Health, Conn
)
from ninjamagic.pathfind import get_next_step


def _find_nearest_player(map_id: int, y: int, x: int, aggro_range: int) -> int | None:
    """Find the nearest player within aggro range."""
    nearest = None
    nearest_dist = float('inf')

    for eid, (conn, transform, health) in esper.get_components(Conn, Transform, Health):
        if transform.map_id != map_id:
            continue
        if health.condition == "dead":
            continue

        dist = abs(transform.y - y) + abs(transform.x - x)
        if dist <= aggro_range and dist < nearest_dist:
            nearest_dist = dist
            nearest = eid

    return nearest


def _is_adjacent(y1: int, x1: int, y2: int, x2: int) -> bool:
    """Check if two positions are adjacent (including diagonal)."""
    return abs(y1 - y2) <= 1 and abs(x1 - x2) <= 1 and (y1, x1) != (y2, x2)


def process_swarm(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process behavior for all swarm mobs.

    Swarm behavior:
    - Find nearest player within aggro range
    - Path toward player
    - Attack when adjacent
    - Simple, direct, no tactics
    """
    for eid, (mob, behavior, transform) in esper.get_components(Mob, MobBehavior, Transform):
        if mob.mob_type != MobType.SWARM:
            continue

        # Cooldown
        if behavior.cooldown > 0:
            behavior.cooldown -= 1.0 / 240.0  # Assuming 240 TPS
            continue

        # Find target if none
        if behavior.target_entity is None:
            target = _find_nearest_player(
                transform.map_id, transform.y, transform.x, mob.aggro_range
            )
            if target:
                behavior.target_entity = target
                behavior.state = BehaviorState.PATHING

        # No target? Stay idle
        if behavior.target_entity is None:
            behavior.state = BehaviorState.IDLE
            continue

        # Get target position
        if not esper.entity_exists(behavior.target_entity):
            behavior.target_entity = None
            behavior.state = BehaviorState.IDLE
            continue

        target_transform = esper.component_for_entity(behavior.target_entity, Transform)

        # Adjacent? Attack!
        if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
            behavior.state = BehaviorState.ENGAGING
            bus.pulse(bus.Melee(source=eid, target=behavior.target_entity))
            behavior.cooldown = 1.0  # 1 second attack cooldown
            continue

        # Not adjacent? Move toward target
        behavior.state = BehaviorState.PATHING
        next_pos = get_next_step(
            current=(transform.y, transform.x),
            goal=(target_transform.y, target_transform.x),
            walkable_check=walkable_check,
        )

        if next_pos:
            dy = next_pos[0] - transform.y
            dx = next_pos[1] - transform.x
            direction = _direction_to_compass(dy, dx)
            bus.pulse(bus.MoveCompass(source=eid, direction=direction))


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
    return "n"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_behavior.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/behavior/ tests/test_behavior.py
git commit -m "feat(behavior): add swarm mob behavior"
```

---

## Task 3: Pack Behavior

**Files:**
- Create: `ninjamagic/behavior/pack.py`
- Test: `tests/test_behavior.py`

**Step 1: Write the failing test**

```python
# tests/test_behavior.py - add these tests

def test_pack_has_leader():
    """Pack mobs follow a leader."""
    from ninjamagic.behavior.pack import process_pack, assign_pack_leaders

    esper.clear_database()
    map_id = esper.create_entity()

    # Create pack mobs
    mobs = []
    for i in range(3):
        mob = esper.create_entity()
        esper.add_component(mob, Transform(map_id=map_id, y=20+i, x=20))
        esper.add_component(mob, Mob(mob_type=MobType.PACK))
        esper.add_component(mob, MobBehavior())
        esper.add_component(mob, Health())
        mobs.append(mob)

    # Assign leaders
    assign_pack_leaders()

    # One should be leader (no pack_leader), others follow
    leaders = [m for m in mobs if esper.component_for_entity(m, MobBehavior).pack_leader is None]
    followers = [m for m in mobs if esper.component_for_entity(m, MobBehavior).pack_leader is not None]

    assert len(leaders) == 1
    assert len(followers) == 2


def test_pack_flanks_target():
    """Pack followers flank the target instead of direct attack."""
    from ninjamagic.behavior.pack import process_pack

    esper.clear_database()
    map_id = esper.create_entity()

    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player, Health())
    esper.add_component(player, Conn())

    # Leader mob
    leader = esper.create_entity()
    esper.add_component(leader, Transform(map_id=map_id, y=15, x=10))
    esper.add_component(leader, Mob(mob_type=MobType.PACK, aggro_range=10))
    esper.add_component(leader, MobBehavior(target_entity=player))
    esper.add_component(leader, Health())

    # Follower mob
    follower = esper.create_entity()
    esper.add_component(follower, Transform(map_id=map_id, y=15, x=12))
    esper.add_component(follower, Mob(mob_type=MobType.PACK))
    esper.add_component(follower, MobBehavior(pack_leader=leader, target_entity=player))
    esper.add_component(follower, Health())

    walkable = lambda y, x: True
    process_pack(walkable_check=walkable)

    # Follower should be flanking (trying to get to opposite side)
    follower_behavior = esper.component_for_entity(follower, MobBehavior)
    assert follower_behavior.state == BehaviorState.FLANKING

    bus.clear()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_behavior.py::test_pack_has_leader -v`
Expected: FAIL with "No module named 'ninjamagic.behavior.pack'"

**Step 3: Create pack behavior module**

```python
# ninjamagic/behavior/pack.py
"""Pack mob behavior: coordinated group that flanks and surrounds."""

import esper
import math
from typing import Callable
from ninjamagic import bus
from ninjamagic.component import (
    Mob, MobType, MobBehavior, BehaviorState, Transform, Health, Conn
)
from ninjamagic.pathfind import get_next_step


def assign_pack_leaders() -> None:
    """Assign pack leaders for groups of nearby pack mobs."""
    # Group pack mobs by proximity
    pack_mobs = []
    for eid, (mob, transform) in esper.get_components(Mob, Transform):
        if mob.mob_type == MobType.PACK:
            pack_mobs.append((eid, transform))

    if not pack_mobs:
        return

    # Simple grouping: first mob in each cluster is leader
    assigned = set()
    GROUP_RADIUS = 10

    for eid, transform in pack_mobs:
        if eid in assigned:
            continue

        # This mob is a leader
        behavior = esper.component_for_entity(eid, MobBehavior)
        behavior.pack_leader = None  # Leaders have no leader
        assigned.add(eid)

        # Find followers
        for other_eid, other_transform in pack_mobs:
            if other_eid in assigned:
                continue
            if other_transform.map_id != transform.map_id:
                continue

            dist = abs(other_transform.y - transform.y) + abs(other_transform.x - transform.x)
            if dist <= GROUP_RADIUS:
                other_behavior = esper.component_for_entity(other_eid, MobBehavior)
                other_behavior.pack_leader = eid
                assigned.add(other_eid)


def _get_flank_position(
    target_y: int, target_x: int,
    leader_y: int, leader_x: int,
    follower_index: int
) -> tuple[int, int]:
    """Calculate a flanking position for a follower.

    Tries to position on opposite/perpendicular side from leader.
    """
    # Direction from target to leader
    dy = leader_y - target_y
    dx = leader_x - target_x

    # Rotate 90 or 180 degrees based on follower index
    if follower_index % 2 == 0:
        # Opposite side
        flank_y = target_y - dy
        flank_x = target_x - dx
    else:
        # Perpendicular
        flank_y = target_y + dx
        flank_x = target_x - dy

    return (flank_y, flank_x)


def process_pack(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process behavior for all pack mobs.

    Pack behavior:
    - Leaders find targets and engage directly
    - Followers flank the target
    - Coordinated attacks (could add timing later)
    """
    for eid, (mob, behavior, transform) in esper.get_components(Mob, MobBehavior, Transform):
        if mob.mob_type != MobType.PACK:
            continue

        if behavior.cooldown > 0:
            behavior.cooldown -= 1.0 / 240.0
            continue

        # Is this a leader or follower?
        is_leader = behavior.pack_leader is None

        if is_leader:
            _process_leader(eid, mob, behavior, transform, walkable_check)
        else:
            _process_follower(eid, mob, behavior, transform, walkable_check)


def _process_leader(eid, mob, behavior, transform, walkable_check):
    """Leader behavior: find target, engage directly."""
    # Similar to swarm but shares target with pack
    from ninjamagic.behavior.swarm import _find_nearest_player, _is_adjacent, _direction_to_compass

    if behavior.target_entity is None:
        target = _find_nearest_player(
            transform.map_id, transform.y, transform.x, mob.aggro_range
        )
        if target:
            behavior.target_entity = target
            behavior.state = BehaviorState.PATHING

            # Share target with followers
            for f_eid, (f_mob, f_behavior) in esper.get_components(Mob, MobBehavior):
                if f_behavior.pack_leader == eid:
                    f_behavior.target_entity = target

    if behavior.target_entity is None:
        behavior.state = BehaviorState.IDLE
        return

    if not esper.entity_exists(behavior.target_entity):
        behavior.target_entity = None
        return

    target_transform = esper.component_for_entity(behavior.target_entity, Transform)

    if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
        behavior.state = BehaviorState.ENGAGING
        bus.pulse(bus.Melee(source=eid, target=behavior.target_entity))
        behavior.cooldown = 1.5
        return

    behavior.state = BehaviorState.PATHING
    next_pos = get_next_step(
        current=(transform.y, transform.x),
        goal=(target_transform.y, target_transform.x),
        walkable_check=walkable_check,
    )
    if next_pos:
        dy = next_pos[0] - transform.y
        dx = next_pos[1] - transform.x
        bus.pulse(bus.MoveCompass(source=eid, direction=_direction_to_compass(dy, dx)))


def _process_follower(eid, mob, behavior, transform, walkable_check):
    """Follower behavior: flank the target."""
    from ninjamagic.behavior.swarm import _is_adjacent, _direction_to_compass

    if behavior.target_entity is None or behavior.pack_leader is None:
        behavior.state = BehaviorState.IDLE
        return

    if not esper.entity_exists(behavior.target_entity) or not esper.entity_exists(behavior.pack_leader):
        behavior.target_entity = None
        return

    target_transform = esper.component_for_entity(behavior.target_entity, Transform)
    leader_transform = esper.component_for_entity(behavior.pack_leader, Transform)

    # Adjacent to target? Attack!
    if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
        behavior.state = BehaviorState.ENGAGING
        bus.pulse(bus.Melee(source=eid, target=behavior.target_entity))
        behavior.cooldown = 1.5
        return

    # Otherwise, move to flank position
    behavior.state = BehaviorState.FLANKING
    flank_pos = _get_flank_position(
        target_transform.y, target_transform.x,
        leader_transform.y, leader_transform.x,
        eid % 2  # Simple index for variety
    )

    next_pos = get_next_step(
        current=(transform.y, transform.x),
        goal=flank_pos,
        walkable_check=walkable_check,
    )
    if next_pos:
        dy = next_pos[0] - transform.y
        dx = next_pos[1] - transform.x
        bus.pulse(bus.MoveCompass(source=eid, direction=_direction_to_compass(dy, dx)))
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_behavior.py -k pack -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/behavior/pack.py tests/test_behavior.py
git commit -m "feat(behavior): add pack mob behavior with flanking"
```

---

## Task 4: Death Knight Behavior

**Files:**
- Create: `ninjamagic/behavior/death_knight.py`
- Test: `tests/test_behavior.py`

**Step 1: Write the failing test**

```python
# tests/test_behavior.py - add this test

def test_death_knight_targets_single_player():
    """Death knight targets one player and fights to the death."""
    from ninjamagic.behavior.death_knight import process_death_knight

    esper.clear_database()
    map_id = esper.create_entity()

    # Two players
    player1 = esper.create_entity()
    esper.add_component(player1, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player1, Health())
    esper.add_component(player1, Conn())

    player2 = esper.create_entity()
    esper.add_component(player2, Transform(map_id=map_id, y=10, x=20))
    esper.add_component(player2, Health())
    esper.add_component(player2, Conn())

    # Death knight
    dk = esper.create_entity()
    esper.add_component(dk, Transform(map_id=map_id, y=15, x=15))
    esper.add_component(dk, Mob(mob_type=MobType.DEATH_KNIGHT, aggro_range=20))
    esper.add_component(dk, MobBehavior())
    esper.add_component(dk, Health())

    walkable = lambda y, x: True
    process_death_knight(walkable_check=walkable)

    behavior = esper.component_for_entity(dk, MobBehavior)

    # Should target one player and stick with them
    assert behavior.target_entity in [player1, player2]
    first_target = behavior.target_entity

    # Process again - should keep same target
    process_death_knight(walkable_check=walkable)
    assert behavior.target_entity == first_target

    bus.clear()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_behavior.py::test_death_knight_targets_single_player -v`
Expected: FAIL with "No module named 'ninjamagic.behavior.death_knight'"

**Step 3: Create death knight behavior module**

```python
# ninjamagic/behavior/death_knight.py
"""Death Knight behavior: strong 1v1 duelist that locks onto a single target."""

import esper
from typing import Callable
from ninjamagic import bus
from ninjamagic.component import (
    Mob, MobType, MobBehavior, BehaviorState, Transform, Health, Conn
)
from ninjamagic.pathfind import get_next_step
from ninjamagic.behavior.swarm import _find_nearest_player, _is_adjacent, _direction_to_compass


def process_death_knight(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process behavior for death knight mobs.

    Death Knight behavior:
    - Locks onto a single target and fights to the death
    - Slower but more powerful attacks
    - Won't switch targets unless current dies
    - More tactical movement (doesn't charge blindly)
    """
    for eid, (mob, behavior, transform) in esper.get_components(Mob, MobBehavior, Transform):
        if mob.mob_type != MobType.DEATH_KNIGHT:
            continue

        if behavior.cooldown > 0:
            behavior.cooldown -= 1.0 / 240.0
            continue

        # Lock onto target - only switch if target dies/disappears
        if behavior.target_entity is not None:
            if not esper.entity_exists(behavior.target_entity):
                behavior.target_entity = None
            else:
                target_health = esper.component_for_entity(behavior.target_entity, Health)
                if target_health.condition == "dead":
                    behavior.target_entity = None

        # Find new target if needed
        if behavior.target_entity is None:
            target = _find_nearest_player(
                transform.map_id, transform.y, transform.x, mob.aggro_range
            )
            if target:
                behavior.target_entity = target
                behavior.state = BehaviorState.PATHING
                # Could announce: "The death knight sets its gaze upon you."

        if behavior.target_entity is None:
            behavior.state = BehaviorState.IDLE
            continue

        target_transform = esper.component_for_entity(behavior.target_entity, Transform)

        # Adjacent? Heavy attack
        if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
            behavior.state = BehaviorState.ENGAGING
            bus.pulse(bus.Melee(source=eid, target=behavior.target_entity))
            behavior.cooldown = 2.0  # Slower attacks
            continue

        # Approach with purpose
        behavior.state = BehaviorState.PATHING
        next_pos = get_next_step(
            current=(transform.y, transform.x),
            goal=(target_transform.y, target_transform.x),
            walkable_check=walkable_check,
        )

        if next_pos:
            dy = next_pos[0] - transform.y
            dx = next_pos[1] - transform.x
            bus.pulse(bus.MoveCompass(source=eid, direction=_direction_to_compass(dy, dx)))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_behavior.py::test_death_knight_targets_single_player -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/behavior/death_knight.py tests/test_behavior.py
git commit -m "feat(behavior): add death knight 1v1 duelist behavior"
```

---

## Task 5: Boss Behavior (Special Encounter)

**Files:**
- Create: `ninjamagic/behavior/boss.py`
- Test: `tests/test_behavior.py`

**Step 1: Write the failing test**

```python
# tests/test_behavior.py - add this test

def test_boss_spawns_adds():
    """Boss periodically spawns add mobs."""
    from ninjamagic.behavior.boss import process_boss

    esper.clear_database()
    map_id = esper.create_entity()

    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player, Health())
    esper.add_component(player, Conn())

    boss = esper.create_entity()
    esper.add_component(boss, Transform(map_id=map_id, y=20, x=20))
    esper.add_component(boss, Mob(mob_type=MobType.BOSS, aggro_range=30))
    esper.add_component(boss, MobBehavior(target_entity=player))
    esper.add_component(boss, Health(cur=200.0))

    # Initial mob count
    initial_mobs = len(list(esper.get_component(Mob)))

    # Process boss behavior (simulate being in summon state)
    behavior = esper.component_for_entity(boss, MobBehavior)
    behavior.state = BehaviorState.SUMMONING

    walkable = lambda y, x: True
    process_boss(walkable_check=walkable, map_id=map_id)

    # Should have spawned adds
    final_mobs = len(list(esper.get_component(Mob)))
    assert final_mobs > initial_mobs

    bus.clear()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_behavior.py::test_boss_spawns_adds -v`
Expected: FAIL with "No module named 'ninjamagic.behavior.boss'"

**Step 3: Create boss behavior module**

```python
# ninjamagic/behavior/boss.py
"""Boss behavior: powerful enemy that spawns adds."""

import esper
from typing import Callable
from ninjamagic import bus
from ninjamagic.component import (
    Mob, MobType, MobBehavior, BehaviorState, Transform, Health, Conn
)
from ninjamagic.pathfind import get_next_step
from ninjamagic.spawn import create_mob
from ninjamagic.behavior.swarm import _find_nearest_player, _is_adjacent, _direction_to_compass


# Boss spawns adds every N seconds
SUMMON_INTERVAL = 10.0
# Number of adds per summon
ADDS_PER_SUMMON = 2


def process_boss(*, walkable_check: Callable[[int, int], bool], map_id: int) -> None:
    """Process behavior for boss mobs.

    Boss behavior:
    - Targets nearest player
    - Periodically spawns adds (swarm mobs)
    - Heavy attacks with long cooldowns
    - Stays in place more, lets adds do work
    """
    for eid, (mob, behavior, transform) in esper.get_components(Mob, MobBehavior, Transform):
        if mob.mob_type != MobType.BOSS:
            continue

        if behavior.cooldown > 0:
            behavior.cooldown -= 1.0 / 240.0
            continue

        # Find target if needed
        if behavior.target_entity is None:
            target = _find_nearest_player(
                transform.map_id, transform.y, transform.x, mob.aggro_range
            )
            if target:
                behavior.target_entity = target

        if behavior.target_entity is None:
            behavior.state = BehaviorState.IDLE
            continue

        if not esper.entity_exists(behavior.target_entity):
            behavior.target_entity = None
            continue

        target_transform = esper.component_for_entity(behavior.target_entity, Transform)

        # Check for summon phase
        if behavior.state == BehaviorState.SUMMONING:
            _spawn_adds(transform.map_id, transform.y, transform.x, map_id)
            behavior.state = BehaviorState.ENGAGING
            behavior.cooldown = SUMMON_INTERVAL
            continue

        # Adjacent? Attack
        if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
            behavior.state = BehaviorState.ENGAGING
            bus.pulse(bus.Melee(source=eid, target=behavior.target_entity))
            behavior.cooldown = 3.0  # Very slow but powerful

            # Maybe summon after attack
            health = esper.component_for_entity(eid, Health)
            if health.cur < 100.0:  # Summon more when hurt
                behavior.state = BehaviorState.SUMMONING
            continue

        # Move toward target (slowly)
        behavior.state = BehaviorState.PATHING
        next_pos = get_next_step(
            current=(transform.y, transform.x),
            goal=(target_transform.y, target_transform.x),
            walkable_check=walkable_check,
        )

        if next_pos:
            dy = next_pos[0] - transform.y
            dx = next_pos[1] - transform.x
            bus.pulse(bus.MoveCompass(source=eid, direction=_direction_to_compass(dy, dx)))
            behavior.cooldown = 0.5  # Move slowly


def _spawn_adds(map_id: int, y: int, x: int, target_map: int) -> None:
    """Spawn add mobs near the boss."""
    import random

    for _ in range(ADDS_PER_SUMMON):
        # Random offset
        offset_y = random.randint(-3, 3)
        offset_x = random.randint(-3, 3)

        create_mob(
            mob_type=MobType.SWARM,
            map_id=target_map,
            y=y + offset_y,
            x=x + offset_x,
            name="spawn",
        )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_behavior.py::test_boss_spawns_adds -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/behavior/boss.py tests/test_behavior.py
git commit -m "feat(behavior): add boss behavior with add spawning"
```

---

## Task 6: Unified Behavior Processor

**Files:**
- Create: `ninjamagic/behavior/__init__.py`
- Modify: `ninjamagic/mob_ai.py`

**Step 1: Create unified processor**

```python
# ninjamagic/behavior/__init__.py
"""Mob behavior system."""

from typing import Callable
from ninjamagic.behavior.swarm import process_swarm
from ninjamagic.behavior.pack import process_pack, assign_pack_leaders
from ninjamagic.behavior.death_knight import process_death_knight
from ninjamagic.behavior.boss import process_boss


def process_all_behaviors(
    *,
    walkable_check: Callable[[int, int], bool],
    map_id: int,
) -> None:
    """Process behavior for all mob types."""
    process_swarm(walkable_check=walkable_check)
    process_pack(walkable_check=walkable_check)
    process_death_knight(walkable_check=walkable_check)
    process_boss(walkable_check=walkable_check, map_id=map_id)
```

**Step 2: Update mob_ai.py to use unified processor**

```python
# ninjamagic/mob_ai.py - replace with:

from ninjamagic.behavior import process_all_behaviors, assign_pack_leaders


def process_mob_ai(*, walkable_check, map_id: int) -> None:
    """Process AI for all mobs."""
    assign_pack_leaders()  # Run occasionally
    process_all_behaviors(walkable_check=walkable_check, map_id=map_id)
```

**Step 3: Commit**

```bash
git add ninjamagic/behavior/__init__.py ninjamagic/mob_ai.py
git commit -m "feat(behavior): unify mob behavior processors"
```

---

## Task 7: Spawn Different Phenotypes

**Files:**
- Modify: `ninjamagic/spawn.py`

**Step 1: Add phenotype selection to spawning**

```python
# ninjamagic/spawn.py - modify process_spawning to spawn different types

import random
from ninjamagic.phases import Phase

# Spawn weights by phase
SPAWN_WEIGHTS = {
    Phase.DAY: {MobType.SWARM: 0.8, MobType.PACK: 0.2},
    Phase.EVENING: {MobType.SWARM: 0.5, MobType.PACK: 0.4, MobType.DEATH_KNIGHT: 0.1},
    Phase.WAVES: {MobType.SWARM: 0.4, MobType.PACK: 0.4, MobType.DEATH_KNIGHT: 0.15, MobType.BOSS: 0.05},
    Phase.FADE: {MobType.SWARM: 0.6, MobType.PACK: 0.4},
    Phase.REST: {},  # No spawning
}

# Names by type
MOB_NAMES = {
    MobType.SWARM: ["goblin", "rat", "crawler"],
    MobType.PACK: ["wolf", "bandit", "hound"],
    MobType.DEATH_KNIGHT: ["death knight", "revenant", "shade"],
    MobType.BOSS: ["lich", "demon", "abomination"],
}


def _choose_mob_type(phase: Phase) -> MobType:
    """Choose a mob type based on phase weights."""
    weights = SPAWN_WEIGHTS.get(phase, {MobType.SWARM: 1.0})
    if not weights:
        return MobType.SWARM

    types = list(weights.keys())
    probs = list(weights.values())
    return random.choices(types, weights=probs)[0]


def _choose_mob_name(mob_type: MobType) -> str:
    """Choose a random name for a mob type."""
    names = MOB_NAMES.get(mob_type, ["creature"])
    return random.choice(names)


# Then in process_spawning, replace the create_mob call:
mob_type = _choose_mob_type(phase)
name = _choose_mob_name(mob_type)

eid = create_mob(
    mob_type=mob_type,
    map_id=map_id,
    y=y,
    x=x,
    name=name,
)
```

**Step 2: Commit**

```bash
git add ninjamagic/spawn.py
git commit -m "feat(spawn): spawn different mob phenotypes based on phase"
```

---

## Summary

After completing all tasks, you will have:

1. **MobBehavior component** - tracks state, target, cooldown, pack leader
2. **Swarm behavior** - simple, direct, attacks in numbers
3. **Pack behavior** - leader/follower, flanking tactics
4. **Death Knight behavior** - 1v1 duelist, locks onto single target
5. **Boss behavior** - spawns adds, heavy attacks
6. **Unified processor** - dispatches to appropriate behavior
7. **Phenotype spawning** - different types based on phase

**Dependencies:** Requires Mob Spawning and Wave System plans.

**Q1 Stretch:** Invader behavior (agentic AI) deferred - requires more sophisticated AI.

**Next plan:** Pilgrimage (anchor creation mechanic)
