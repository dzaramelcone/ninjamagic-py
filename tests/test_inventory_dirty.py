import esper
import ninjamagic.bus as bus
import ninjamagic.move as move
from ninjamagic.component import InventoryDirty


def test_move_entity_marks_dirty():
    eid = esper.create_entity()
    bus.pulse(bus.MoveEntity(source=eid, container=1, slot=""))
    move.process()
    assert esper.has_component(eid, InventoryDirty)
