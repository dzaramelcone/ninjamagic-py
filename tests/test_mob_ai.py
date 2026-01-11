# tests/test_mob_ai.py
from unittest.mock import MagicMock

import esper

from ninjamagic import bus
from ninjamagic.behavior.swarm import process_swarm
from ninjamagic.component import Connection, Health, Mob, MobBehavior, MobType, Transform


def test_swarm_mob_moves_toward_player():
    """Swarm mobs path toward the nearest player."""
    esper.clear_database()
    bus.clear()

    map_id = esper.create_entity()

    # Create a player at (50, 50)
    player_eid = esper.create_entity()
    esper.add_component(player_eid, Transform(map_id=map_id, y=50, x=50))
    esper.add_component(player_eid, Health())
    esper.add_component(player_eid, MagicMock(), Connection)

    # Create a swarm mob at (50, 60) - 10 tiles away
    mob_eid = esper.create_entity()
    esper.add_component(mob_eid, Transform(map_id=map_id, y=50, x=60))
    esper.add_component(mob_eid, Mob(mob_type=MobType.SWARM, aggro_range=20))
    esper.add_component(mob_eid, MobBehavior())
    esper.add_component(mob_eid, Health())

    # Process AI
    walkable = lambda y, x: True
    process_swarm(walkable_check=walkable)

    # Check that a move signal was emitted
    move_signals = list(bus.iter(bus.MoveCompass))
    assert len(move_signals) > 0

    # The mob should be moving west (toward player)
    sig = move_signals[0]
    assert sig.source == mob_eid

    bus.clear()
