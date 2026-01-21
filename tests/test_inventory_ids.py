from ninjamagic.component import ItemKey


def test_item_key_equality():
    key1 = ItemKey(key="torch")
    key2 = ItemKey(key="torch")
    key3 = ItemKey(key="sword")
    assert key1 == key2
    assert key1 != key3
