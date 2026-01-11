# ninjamagic/spawn.py
"""Mob spawning system: spawn from darkness, path toward light."""

import math
import random
from collections.abc import Callable

import esper

from ninjamagic.component import (
    Glyph,
    Health,
    Mob,
    MobType,
    Noun,
    Skills,
    Stance,
    Stats,
    Transform,
)
from ninjamagic.util import Pronouns

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
    esper.add_component(eid, Health(cur=config["health"], stress=0.0))
    esper.add_component(eid, Noun(value=name, pronoun=Pronouns.IT))
    esper.add_component(eid, Stance())
    esper.add_component(eid, Skills())
    esper.add_component(eid, Stats())
    esper.add_component(eid, (config["glyph"], config["hue"], 0.6, 0.7), Glyph)

    return eid
