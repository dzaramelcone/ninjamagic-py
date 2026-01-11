"""Swarm mob behavior: weak, fast, attacks in numbers."""

from collections.abc import Callable

import esper

from ninjamagic import bus
from ninjamagic.component import (
    BehaviorState,
    Connection,
    Health,
    Mob,
    MobBehavior,
    MobType,
    Transform,
)
from ninjamagic.pathfind import get_next_step
from ninjamagic.util import Compass


def _find_nearest_player(map_id: int, y: int, x: int, aggro_range: int) -> int | None:
    """Find the nearest player within aggro range."""
    nearest = None
    nearest_dist = float("inf")

    for eid, (_, transform, health) in esper.get_components(Connection, Transform, Health):
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
    return Compass.NORTH


def process_swarm(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process behavior for all swarm mobs."""
    for eid, (mob, behavior, transform) in esper.get_components(Mob, MobBehavior, Transform):
        if mob.mob_type != MobType.SWARM:
            continue

        # Cooldown
        if behavior.cooldown > 0:
            behavior.cooldown -= 1.0 / 240.0
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
            bus.pulse(bus.Melee(source=eid, target=behavior.target_entity, verb="slash"))
            behavior.cooldown = 1.0
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
            bus.pulse(bus.MoveCompass(source=eid, dir=direction))
