"""Behavior priority queue system for mob AI.

Mobs have a BehaviorQueue component with a list of behaviors to try in priority order.
Each tick, the system processes each mob's queue, trying behaviors until one succeeds.
"""

from dataclasses import dataclass as behavior

import esper

from ninjamagic import bus
from ninjamagic.component import (
    Anchor,
    Connection,
    EntityId,
    Health,
    Target,
    Transform,
    transform,
)
from ninjamagic.dijkstra import DijkstraMap
from ninjamagic.util import Looptime
from ninjamagic.world.state import can_enter

# Behavior type will be defined after the dataclasses
# Use Any for now to avoid forward reference issues


@behavior(frozen=True, slots=True)
class SelectNearestPlayer:
    """Sets Target component to nearest player."""

    pass


@behavior(frozen=True, slots=True)
class SelectNearestAnchor:
    """Sets Target component to nearest anchor."""

    pass


@behavior(frozen=True, slots=True)
class PathTowardEntity:
    """Path toward Target."""

    pass


@behavior(frozen=True, slots=True, kw_only=True)
class PathTowardCoordinate:
    """Path toward specific coordinate."""

    y: int
    x: int


@behavior(frozen=True, slots=True)
class Attack:
    """Attack Target if adjacent."""

    pass


@behavior(frozen=True, slots=True)
class FlankTarget:
    """Move to flanking position around Target."""

    pass


@behavior(frozen=True, slots=True)
class FleeFromEntity:
    """Flee from Target."""

    pass


@behavior(frozen=True, slots=True)
class Wait:
    """Do nothing this tick."""

    pass


@behavior(frozen=True, slots=True, kw_only=True)
class UseAbility:
    """Use a specific ability."""

    ability: str


# Type alias for all behavior types
Behavior = (
    SelectNearestPlayer
    | SelectNearestAnchor
    | PathTowardEntity
    | PathTowardCoordinate
    | Attack
    | FlankTarget
    | FleeFromEntity
    | Wait
    | UseAbility
)


def _manhattan_distance(y1: int, x1: int, y2: int, x2: int) -> int:
    return abs(y1 - y2) + abs(x1 - x2)


def _is_adjacent(t1: Transform, t2: Transform) -> bool:
    """Check if two transforms are adjacent (Manhattan distance <= 1, same map)."""
    if t1.map_id != t2.map_id:
        return False
    return _manhattan_distance(t1.y, t1.x, t2.y, t2.x) <= 1


def _find_nearest_player(eid: EntityId) -> EntityId | None:
    """Find the nearest player to entity."""
    loc = esper.try_component(eid, Transform)
    if not loc:
        return None

    nearest = None
    nearest_dist = float("inf")

    for player_eid, (player_loc, _) in esper.get_components(Transform, Connection):
        if player_eid == eid:
            continue
        if player_loc.map_id != loc.map_id:
            continue

        dist = _manhattan_distance(loc.y, loc.x, player_loc.y, player_loc.x)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = player_eid

    return nearest


def _find_nearest_anchor(eid: EntityId) -> EntityId | None:
    """Find the nearest anchor to entity."""
    loc = esper.try_component(eid, Transform)
    if not loc:
        return None

    nearest = None
    nearest_dist = float("inf")

    for anchor_eid, (anchor_loc, _) in esper.get_components(Transform, Anchor):
        if anchor_eid == eid:
            continue
        if anchor_loc.map_id != loc.map_id:
            continue

        dist = _manhattan_distance(loc.y, loc.x, anchor_loc.y, anchor_loc.x)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = anchor_eid

    return nearest


def _get_blocked_cells(
    map_id: EntityId, center_y: int, center_x: int, radius: int = 16
) -> set[tuple[int, int]]:
    """Get blocked cells around a center point."""
    blocked = set()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            y, x = center_y + dy, center_x + dx
            if not can_enter(map_id=map_id, y=y, x=x):
                blocked.add((y, x))
    return blocked


def can_execute(b: Behavior, eid: EntityId) -> bool:
    """Check if behavior can be executed."""
    match b:
        case SelectNearestPlayer():
            return _find_nearest_player(eid) is not None

        case SelectNearestAnchor():
            return _find_nearest_anchor(eid) is not None

        case PathTowardEntity():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False
            loc = esper.try_component(eid, Transform)
            target_loc = esper.try_component(target.entity, Transform)
            if not loc or not target_loc:
                return False
            if loc.map_id != target_loc.map_id:
                return False
            # Can execute if not already at target
            return not (loc.y == target_loc.y and loc.x == target_loc.x)

        case PathTowardCoordinate(y=ty, x=tx):
            loc = esper.try_component(eid, Transform)
            if not loc:
                return False
            # Can execute if not already at coordinate
            return not (loc.y == ty and loc.x == tx)

        case Attack():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False
            loc = esper.try_component(eid, Transform)
            target_loc = esper.try_component(target.entity, Transform)
            if not loc or not target_loc:
                return False
            # Can attack if adjacent
            return _is_adjacent(loc, target_loc)

        case FlankTarget():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False
            loc = esper.try_component(eid, Transform)
            target_loc = esper.try_component(target.entity, Transform)
            if not loc or not target_loc:
                return False
            if loc.map_id != target_loc.map_id:
                return False
            # Can flank if not already adjacent
            return not _is_adjacent(loc, target_loc)

        case FleeFromEntity():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False
            return esper.has_component(eid, Transform)

        case Wait():
            return True

        case UseAbility(ability=_):
            # TODO: Check if ability is available and off cooldown
            return True

        case _:
            return False


def execute(b: Behavior, eid: EntityId) -> bool:
    """Execute behavior. Returns True if successful."""
    match b:
        case SelectNearestPlayer():
            player = _find_nearest_player(eid)
            if not player:
                return False
            if esper.has_component(eid, Target):
                esper.remove_component(eid, Target)
            esper.add_component(eid, Target(entity=player))
            return True

        case SelectNearestAnchor():
            anchor = _find_nearest_anchor(eid)
            if not anchor:
                return False
            if esper.has_component(eid, Target):
                esper.remove_component(eid, Target)
            esper.add_component(eid, Target(entity=anchor))
            return True

        case PathTowardEntity():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False
            loc = transform(eid)
            target_loc = transform(target.entity)

            # Use DijkstraMap to find direction
            dm = DijkstraMap()
            blocked = _get_blocked_cells(loc.map_id, loc.y, loc.x)
            dm.compute(goals=[(target_loc.y, target_loc.x)], blocked=blocked)

            direction = dm.get_direction_toward(loc.y, loc.x)
            if not direction:
                return False

            dy, dx = direction.to_vector()
            new_y, new_x = loc.y + dy, loc.x + dx

            if not can_enter(map_id=loc.map_id, y=new_y, x=new_x):
                return False

            bus.pulse(bus.MovePosition(source=eid, to_map_id=loc.map_id, to_y=new_y, to_x=new_x))
            return True

        case PathTowardCoordinate(y=ty, x=tx):
            loc = transform(eid)

            dm = DijkstraMap()
            blocked = _get_blocked_cells(loc.map_id, loc.y, loc.x)
            dm.compute(goals=[(ty, tx)], blocked=blocked)

            direction = dm.get_direction_toward(loc.y, loc.x)
            if not direction:
                return False

            dy, dx = direction.to_vector()
            new_y, new_x = loc.y + dy, loc.x + dx

            if not can_enter(map_id=loc.map_id, y=new_y, x=new_x):
                return False

            bus.pulse(bus.MovePosition(source=eid, to_map_id=loc.map_id, to_y=new_y, to_x=new_x))
            return True

        case Attack():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False

            loc = transform(eid)
            target_loc = transform(target.entity)

            if not _is_adjacent(loc, target_loc):
                return False

            # Check target is alive
            target_health = esper.try_component(target.entity, Health)
            if target_health and target_health.condition == "dead":
                return False

            bus.pulse(bus.Melee(source=eid, target=target.entity, verb="slash"))
            return True

        case FlankTarget():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False

            loc = transform(eid)
            target_loc = transform(target.entity)

            # Find flanking positions (cells adjacent to target but not in direct line)
            flank_positions = []
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    fy, fx = target_loc.y + dy, target_loc.x + dx
                    if can_enter(map_id=loc.map_id, y=fy, x=fx):
                        # Prefer positions that are diagonal from target
                        if dy != 0 and dx != 0:
                            flank_positions.insert(0, (fy, fx))
                        else:
                            flank_positions.append((fy, fx))

            if not flank_positions:
                return False

            # Path toward nearest flanking position
            dm = DijkstraMap()
            blocked = _get_blocked_cells(loc.map_id, loc.y, loc.x)
            dm.compute(goals=flank_positions, blocked=blocked)

            direction = dm.get_direction_toward(loc.y, loc.x)
            if not direction:
                return False

            dy, dx = direction.to_vector()
            new_y, new_x = loc.y + dy, loc.x + dx

            if not can_enter(map_id=loc.map_id, y=new_y, x=new_x):
                return False

            bus.pulse(bus.MovePosition(source=eid, to_map_id=loc.map_id, to_y=new_y, to_x=new_x))
            return True

        case FleeFromEntity():
            target = esper.try_component(eid, Target)
            if not target or not esper.entity_exists(target.entity):
                return False

            loc = transform(eid)
            target_loc = transform(target.entity)

            dm = DijkstraMap()
            blocked = _get_blocked_cells(loc.map_id, loc.y, loc.x)
            dm.compute(goals=[(target_loc.y, target_loc.x)], blocked=blocked)

            # Flee: move to highest cost neighbor
            direction = dm.get_direction_away(loc.y, loc.x)
            if not direction:
                return False

            dy, dx = direction.to_vector()
            new_y, new_x = loc.y + dy, loc.x + dx

            if not can_enter(map_id=loc.map_id, y=new_y, x=new_x):
                return False

            bus.pulse(bus.MovePosition(source=eid, to_map_id=loc.map_id, to_y=new_y, to_x=new_x))
            return True

        case Wait():
            return True

        case UseAbility(ability=ability_name):
            # TODO: Implement ability usage
            _ = ability_name
            return True

        case _:
            return False


def process_behavior_queue(eid: EntityId, behaviors: list[Behavior]) -> bool:
    """Process behavior queue for an entity.

    Tries behaviors in order until one succeeds.
    Returns True if any behavior executed successfully.
    """
    return any(can_execute(b, eid) and execute(b, eid) for b in behaviors)


def process(now: Looptime) -> None:
    """Process all entities with BehaviorQueue components."""
    # TODO: Wire into game loop in state.py (after act, before combat)
    from ninjamagic.component import BehaviorQueue

    _ = now  # May be used for cooldowns later

    for eid, (queue,) in esper.get_components(BehaviorQueue):
        process_behavior_queue(eid, queue.behaviors)
