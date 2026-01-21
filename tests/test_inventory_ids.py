from ninjamagic.component import InventoryId, ItemKey


def test_inventory_id_defaults():
    assert InventoryId(0) == 0


def test_item_key_equality():
    key1 = ItemKey(key="torch")
    key2 = ItemKey(key="torch")
    key3 = ItemKey(key="sword")
    assert key1 == key2
    assert key1 != key3
