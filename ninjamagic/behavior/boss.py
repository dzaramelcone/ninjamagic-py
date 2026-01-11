"""Boss behavior: powerful enemy that spawns adds."""

import random
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
from ninjamagic.spawn import create_mob

SUMMON_INTERVAL = 10.0
ADDS_PER_SUMMON = 2


def process_boss(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process behavior for boss mobs.

    Boss behavior:
    - Targets nearest player
    - Periodically spawns adds (swarm mobs)
    - Heavy attacks with long cooldowns
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
            _spawn_adds(transform.map_id, transform.y, transform.x)
            behavior.state = BehaviorState.ENGAGING
            behavior.cooldown = SUMMON_INTERVAL
            continue

        # Adjacent? Attack
        if _is_adjacent(transform.y, transform.x, target_transform.y, target_transform.x):
            behavior.state = BehaviorState.ENGAGING
            bus.pulse(bus.Melee(source=eid, target=behavior.target_entity, verb="slash"))
            behavior.cooldown = 3.0  # Very slow but powerful

            # Maybe summon after attack when hurt
            health = esper.component_for_entity(eid, Health)
            if health.cur < 100.0:
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
            bus.pulse(bus.MoveCompass(source=eid, dir=_direction_to_compass(dy, dx)))
            behavior.cooldown = 0.5  # Move slowly


def _spawn_adds(map_id: int, y: int, x: int) -> None:
    """Spawn add mobs near the boss."""
    for _ in range(ADDS_PER_SUMMON):
        offset_y = random.randint(-3, 3)
        offset_x = random.randint(-3, 3)

        create_mob(
            mob_type=MobType.SWARM,
            map_id=map_id,
            y=y + offset_y,
            x=x + offset_x,
            name="spawn",
        )
