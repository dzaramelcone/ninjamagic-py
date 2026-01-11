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
