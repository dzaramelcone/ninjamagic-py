"""Death Knight behavior: strong 1v1 duelist that locks onto a single target."""

from collections.abc import Callable

import esper

from ninjamagic import bus
from ninjamagic.behavior.swarm import _direction_to_compass, _find_nearest_player, _is_adjacent
from ninjamagic.component import (
    BehaviorState,
    Health,
    Mob,
    MobBehavior,
    MobType,
    Transform,
)
from ninjamagic.pathfind import get_next_step


def process_death_knight(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process behavior for death knight mobs.

    Death Knight behavior:
    - Locks onto a single target and fights to the death
    - Slower but more powerful attacks
    - Won't switch targets unless current dies
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

        if behavior.target_entity is None:
            behavior.state = BehaviorState.IDLE
            continue

        target_transform = esper.component_for_entity(behavior.target_entity, Transform)

        # Adjacent? Heavy attack
        if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
            behavior.state = BehaviorState.ENGAGING
            bus.pulse(bus.Melee(source=eid, target=behavior.target_entity, verb="slash"))
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
            bus.pulse(bus.MoveCompass(source=eid, dir=_direction_to_compass(dy, dx)))
