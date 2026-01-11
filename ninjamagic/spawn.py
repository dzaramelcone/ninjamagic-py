# ninjamagic/spawn.py
"""Mob spawning system: spawn from darkness, path toward light."""

import math
import random
from collections.abc import Callable
from dataclasses import dataclass

import esper

from ninjamagic.anchor import get_anchor_positions_with_radii
from ninjamagic.component import (
    Anchor,
    Glyph,
    Health,
    Mob,
    MobBehavior,
    MobType,
    Noun,
    Skills,
    Stance,
    Stats,
    Transform,
)
from ninjamagic.phases import Phase, get_spawn_multiplier
from ninjamagic.util import Pronouns


@dataclass
class SpawnConfig:
    """Configuration for mob spawning."""

    spawn_rate: float = 0.1  # Mobs per second (base rate)
    max_mobs: int = 20  # Maximum mobs on map
    min_distance: int = 30  # Minimum distance from anchors
    max_distance: int = 60  # Maximum distance from anchors


# Track spawn accumulator per map
_spawn_accumulators: dict[int, float] = {}

# Spawn weights by phase
SPAWN_WEIGHTS: dict[Phase, dict[MobType, float]] = {
    Phase.DAY: {MobType.SWARM: 0.8, MobType.PACK: 0.2},
    Phase.EVENING: {MobType.SWARM: 0.5, MobType.PACK: 0.4, MobType.DEATH_KNIGHT: 0.1},
    Phase.WAVES: {
        MobType.SWARM: 0.4,
        MobType.PACK: 0.4,
        MobType.DEATH_KNIGHT: 0.15,
        MobType.BOSS: 0.05,
    },
    Phase.FADE: {MobType.SWARM: 0.6, MobType.PACK: 0.4},
    Phase.REST: {},  # No spawning
}

# Names by type
MOB_NAMES: dict[MobType, list[str]] = {
    MobType.SWARM: ["goblin", "rat", "crawler"],
    MobType.PACK: ["wolf", "bandit", "hound"],
    MobType.DEATH_KNIGHT: ["death knight", "revenant", "shade"],
    MobType.BOSS: ["lich", "demon", "abomination"],
}

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
            max_distance,
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
    esper.add_component(eid, Mob(mob_type=mob_type, aggro_range=config["aggro_range"]))
    esper.add_component(eid, MobBehavior())
    esper.add_component(eid, Health(cur=config["health"], stress=0.0))
    esper.add_component(eid, Noun(value=name, pronoun=Pronouns.IT))
    esper.add_component(eid, Stance())
    esper.add_component(eid, Skills())
    esper.add_component(eid, Stats())
    esper.add_component(eid, (config["glyph"], config["hue"], 0.6, 0.7), Glyph)

    return eid


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


def process_spawning(
    *,
    map_id: int,
    delta_seconds: float,
    config: SpawnConfig,
    walkable_check: Callable[[int, int], bool],
    phase: Phase = Phase.DAY,
) -> list[int]:
    """Process mob spawning for a map.

    Returns list of newly spawned mob entity IDs.
    """
    spawned = []

    # Apply phase multiplier
    multiplier = get_spawn_multiplier(phase)
    if multiplier == 0.0:
        return spawned  # No spawning during this phase

    # Get anchor positions
    anchors = get_anchor_positions_with_radii()
    map_anchors = [(y, x, r) for y, x, r in anchors]

    if not map_anchors:
        return spawned  # No anchors = no spawning

    # Count current mobs
    current_mobs = sum(1 for _ in esper.get_component(Mob))
    if current_mobs >= config.max_mobs:
        return spawned

    # Accumulate spawn progress
    if map_id not in _spawn_accumulators:
        _spawn_accumulators[map_id] = 0.0

    _spawn_accumulators[map_id] += delta_seconds * config.spawn_rate * multiplier

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

        # Choose mob type and name based on phase
        mob_type = _choose_mob_type(phase)
        name = _choose_mob_name(mob_type)

        # Create mob
        eid = create_mob(
            mob_type=mob_type,
            map_id=map_id,
            y=y,
            x=x,
            name=name,
        )

        spawned.append(eid)
        current_mobs += 1

    return spawned


def process_despawning() -> list[int]:
    """Remove mobs that should despawn.

    Returns list of despawned entity IDs.
    """
    despawned = []

    for eid, (_mob, transform) in esper.get_components(Mob, Transform):
        # Check if at an anchor
        for _anchor_eid, (_anchor, anchor_transform) in esper.get_components(Anchor, Transform):
            if anchor_transform.map_id != transform.map_id:
                continue

            dist = abs(transform.y - anchor_transform.y) + abs(transform.x - anchor_transform.x)
            if dist <= 1:
                # At anchor - despawn (later: attack instead)
                esper.delete_entity(eid)
                despawned.append(eid)
                break

    return despawned
