import pytest
import esper

from ninjamagic.component import ContainedBy, InventoryId, OwnerId, Slot
from ninjamagic.inventory import save_owner_inventory


class DummyQuerier:
    async def delete_inventories_for_owner(self, *, owner_id: int) -> None:
        raise AssertionError("delete should not be called before validation")

    async def insert_inventories_for_owner(self, arg) -> None:
        raise AssertionError("insert should not be called before validation")


@pytest.mark.asyncio
async def test_save_owner_inventory_requires_template_id():
    owner = esper.create_entity()
    esper.add_component(owner, 1, OwnerId)

    item = esper.create_entity()
    esper.add_component(item, owner, ContainedBy)
    esper.add_component(item, Slot.ANY)
    esper.add_component(item, 10, InventoryId)

    with pytest.raises(RuntimeError, match="Missing ItemTemplateId"):
        await save_owner_inventory(DummyQuerier(), owner_id=1, owner_entity=owner)
