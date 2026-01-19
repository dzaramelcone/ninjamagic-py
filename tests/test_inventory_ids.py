from ninjamagic.component import InventoryId, ItemTemplateId


def test_inventory_id_defaults():
    assert InventoryId(0) == 0
    assert ItemTemplateId(0) == 0
