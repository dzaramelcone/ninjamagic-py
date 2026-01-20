import esper
import pytest
import ninjamagic.bus as bus
import ninjamagic.inventory as inventory
from ninjamagic.component import Junk


@pytest.mark.asyncio
async def test_junk_cleanup_on_restcheck():
    eid = esper.create_entity(Junk())
    bus.pulse(bus.RestCheck())
    await inventory.process()
    assert not esper.entity_exists(eid)
