from unittest.mock import MagicMock

import esper

from ninjamagic import bus


def _always_walkable(y: int, x: int) -> bool:
    return True


def test_swarm_targets_nearest_player():
    """Swarm mobs target the nearest player."""
    from ninjamagic.behavior.swarm import process_swarm
    from ninjamagic.component import (
        BehaviorState,
        Connection,
        Health,
        Mob,
        MobBehavior,
        MobType,
        Transform,
    )

    esper.clear_database()
    bus.clear()

    map_id = esper.create_entity()

    # Create a player (Connection marks entity as player)
    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player, Health())
    esper.add_component(player, MagicMock(), Connection)

    # Create a swarm mob
    mob = esper.create_entity()
    esper.add_component(mob, Transform(map_id=map_id, y=15, x=15))
    esper.add_component(mob, Mob(mob_type=MobType.SWARM, aggro_range=10))
    esper.add_component(mob, MobBehavior())
    esper.add_component(mob, Health())

    # Process swarm behavior
    process_swarm(walkable_check=_always_walkable)

    # Mob should target player
    behavior = esper.component_for_entity(mob, MobBehavior)
    assert behavior.target_entity == player
    assert behavior.state == BehaviorState.PATHING

    bus.clear()


def test_swarm_attacks_when_adjacent():
    """Swarm mobs attack when next to target."""
    from ninjamagic.behavior.swarm import process_swarm
    from ninjamagic.component import (
        Connection,
        Health,
        Mob,
        MobBehavior,
        MobType,
        Transform,
    )

    esper.clear_database()
    bus.clear()

    map_id = esper.create_entity()

    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player, Health())
    esper.add_component(player, MagicMock(), Connection)

    mob = esper.create_entity()
    esper.add_component(mob, Transform(map_id=map_id, y=10, x=11))  # Adjacent
    esper.add_component(mob, Mob(mob_type=MobType.SWARM))
    esper.add_component(mob, MobBehavior(target_entity=player))
    esper.add_component(mob, Health())

    process_swarm(walkable_check=_always_walkable)

    # Should emit Melee signal
    melee_signals = list(bus.iter(bus.Melee))
    assert len(melee_signals) > 0
    assert melee_signals[0].source == mob
    assert melee_signals[0].target == player

    bus.clear()


def test_pack_has_leader():
    """Pack mobs follow a leader."""
    from ninjamagic.behavior.pack import assign_pack_leaders
    from ninjamagic.component import (
        Health,
        Mob,
        MobBehavior,
        MobType,
        Transform,
    )

    esper.clear_database()
    bus.clear()

    map_id = esper.create_entity()

    # Create pack mobs close together
    mobs = []
    for i in range(3):
        mob = esper.create_entity()
        esper.add_component(mob, Transform(map_id=map_id, y=20 + i, x=20))
        esper.add_component(mob, Mob(mob_type=MobType.PACK))
        esper.add_component(mob, MobBehavior())
        esper.add_component(mob, Health())
        mobs.append(mob)

    # Assign leaders
    assign_pack_leaders()

    # One should be leader (no pack_leader), others follow
    leaders = [m for m in mobs if esper.component_for_entity(m, MobBehavior).pack_leader is None]
    followers = [
        m for m in mobs if esper.component_for_entity(m, MobBehavior).pack_leader is not None
    ]

    assert len(leaders) == 1
    assert len(followers) == 2

    bus.clear()


def test_pack_flanks_target():
    """Pack followers flank the target instead of direct attack."""
    from ninjamagic.behavior.pack import process_pack
    from ninjamagic.component import (
        BehaviorState,
        Connection,
        Health,
        Mob,
        MobBehavior,
        MobType,
        Transform,
    )

    esper.clear_database()
    bus.clear()

    map_id = esper.create_entity()

    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(player, Health())
    esper.add_component(player, MagicMock(), Connection)

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

    process_pack(walkable_check=_always_walkable)

    # Follower should be flanking
    follower_behavior = esper.component_for_entity(follower, MobBehavior)
    assert follower_behavior.state == BehaviorState.FLANKING

    bus.clear()
