"""Mob AI: simple behavior that paths toward anchors."""

from collections.abc import Callable

import esper

from ninjamagic import bus
from ninjamagic.component import Anchor, Mob, Transform
from ninjamagic.pathfind import get_next_step
from ninjamagic.util import Compass


def _get_nearest_anchor(map_id: int, y: int, x: int) -> tuple[int, int] | None:
    """Find the position of the nearest anchor on this map."""
    nearest = None
    nearest_dist = float("inf")

    for _eid, (_anchor, transform) in esper.get_components(Anchor, Transform):
        if transform.map_id != map_id:
            continue

        dist = abs(transform.y - y) + abs(transform.x - x)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = (transform.y, transform.x)

    return nearest


def _direction_to_compass(dy: int, dx: int) -> Compass:
    """Convert delta to compass direction."""
    if dy < 0 and dx == 0:
        return Compass.NORTH
    if dy > 0 and dx == 0:
        return Compass.SOUTH
    if dy == 0 and dx < 0:
        return Compass.WEST
    if dy == 0 and dx > 0:
        return Compass.EAST
    if dy < 0 and dx < 0:
        return Compass.NORTHWEST
    if dy < 0 and dx > 0:
        return Compass.NORTHEAST
    if dy > 0 and dx < 0:
        return Compass.SOUTHWEST
    if dy > 0 and dx > 0:
        return Compass.SOUTHEAST
    return Compass.NORTH  # Fallback


def process_mob_ai(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process AI for all mobs.

    Mobs path toward the nearest anchor.
    """
    for eid, (_mob, transform) in esper.get_components(Mob, Transform):
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
        bus.pulse(bus.MoveCompass(source=eid, dir=direction))
