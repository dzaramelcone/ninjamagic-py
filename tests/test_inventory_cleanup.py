import esper

import ninjamagic.bus as bus
import ninjamagic.inventory as inventory
from ninjamagic.component import DoNotSave


def test_junk_cleanup_on_restcheck():
    eid = esper.create_entity(DoNotSave())
    bus.pulse(bus.RestCheck())
    inventory.process()
    assert not esper.entity_exists(eid)
