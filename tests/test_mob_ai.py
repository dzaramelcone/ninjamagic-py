# tests/test_mob_ai.py
import esper

from ninjamagic import bus
from ninjamagic.component import Anchor, Mob, MobType, Transform
from ninjamagic.mob_ai import process_mob_ai


def test_mob_moves_toward_anchor():
    """Mobs path toward the nearest anchor."""
    esper.clear_database()

    # Create a map
    map_id = esper.create_entity()

    # Create an anchor at (50, 50)
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=50, x=50))
    esper.add_component(anchor_eid, Anchor())

    # Create a mob at (50, 60) - 10 tiles away
    mob_eid = esper.create_entity()
    esper.add_component(mob_eid, Transform(map_id=map_id, y=50, x=60))
    esper.add_component(mob_eid, Mob(mob_type=MobType.SWARM))

    # Process AI
    walkable = lambda y, x: True
    process_mob_ai(walkable_check=walkable)

    # Check that a move signal was emitted
    move_signals = list(bus.iter(bus.MoveCompass))
    assert len(move_signals) > 0

    # The mob should be moving west (toward anchor)
    sig = move_signals[0]
    assert sig.source == mob_eid

    bus.clear()
