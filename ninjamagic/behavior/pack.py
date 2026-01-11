"""Pack mob behavior: coordinated group that flanks and surrounds."""

from collections.abc import Callable

import esper

from ninjamagic import bus
from ninjamagic.behavior.swarm import (
    _direction_to_compass,
    _find_nearest_player,
    _is_adjacent,
)
from ninjamagic.component import (
    BehaviorState,
    Mob,
    MobBehavior,
    MobType,
    Transform,
)
from ninjamagic.pathfind import get_next_step

GROUP_RADIUS = 10


def assign_pack_leaders() -> None:
    """Assign pack leaders for groups of nearby pack mobs."""
    pack_mobs = []
    for eid, (mob, transform) in esper.get_components(Mob, Transform):
        if mob.mob_type == MobType.PACK:
            pack_mobs.append((eid, transform))

    if not pack_mobs:
        return

    assigned: set[int] = set()

    for eid, transform in pack_mobs:
        if eid in assigned:
            continue

        # This mob is a leader
        behavior = esper.component_for_entity(eid, MobBehavior)
        behavior.pack_leader = None
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
    target_y: int,
    target_x: int,
    leader_y: int,
    leader_x: int,
    follower_index: int,
) -> tuple[int, int]:
    """Calculate a flanking position for a follower."""
    dy = leader_y - target_y
    dx = leader_x - target_x

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
    """Process behavior for all pack mobs."""
    for eid, (mob, behavior, transform) in esper.get_components(Mob, MobBehavior, Transform):
        if mob.mob_type != MobType.PACK:
            continue

        if behavior.cooldown > 0:
            behavior.cooldown -= 1.0 / 240.0
            continue

        is_leader = behavior.pack_leader is None

        if is_leader:
            _process_leader(eid, mob, behavior, transform, walkable_check)
        else:
            _process_follower(eid, behavior, transform, walkable_check)


def _process_leader(eid, mob, behavior, transform, walkable_check):
    """Leader behavior: find target, engage directly."""
    if behavior.target_entity is None:
        target = _find_nearest_player(transform.map_id, transform.y, transform.x, mob.aggro_range)
        if target:
            behavior.target_entity = target
            behavior.state = BehaviorState.PATHING

            # Share target with followers
            for _f_eid, (_f_mob, f_behavior) in esper.get_components(Mob, MobBehavior):
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
        bus.pulse(bus.Melee(source=eid, target=behavior.target_entity, verb="slash"))
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
        bus.pulse(bus.MoveCompass(source=eid, dir=_direction_to_compass(dy, dx)))


def _process_follower(eid, behavior, transform, walkable_check):
    """Follower behavior: flank the target."""
    if behavior.target_entity is None or behavior.pack_leader is None:
        behavior.state = BehaviorState.IDLE
        return

    if not esper.entity_exists(behavior.target_entity) or not esper.entity_exists(
        behavior.pack_leader
    ):
        behavior.target_entity = None
        return

    target_transform = esper.component_for_entity(behavior.target_entity, Transform)
    leader_transform = esper.component_for_entity(behavior.pack_leader, Transform)

    # Safety check: ensure all on same map
    if target_transform.map_id != transform.map_id or leader_transform.map_id != transform.map_id:
        behavior.target_entity = None
        behavior.state = BehaviorState.IDLE
        return

    if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
        behavior.state = BehaviorState.ENGAGING
        bus.pulse(bus.Melee(source=eid, target=behavior.target_entity, verb="slash"))
        behavior.cooldown = 1.5
        return

    behavior.state = BehaviorState.FLANKING
    flank_pos = _get_flank_position(
        target_transform.y,
        target_transform.x,
        leader_transform.y,
        leader_transform.x,
        eid % 2,
    )

    next_pos = get_next_step(
        current=(transform.y, transform.x),
        goal=flank_pos,
        walkable_check=walkable_check,
    )
    if next_pos:
        dy = next_pos[0] - transform.y
        dx = next_pos[1] - transform.x
        bus.pulse(bus.MoveCompass(source=eid, dir=_direction_to_compass(dy, dx)))
