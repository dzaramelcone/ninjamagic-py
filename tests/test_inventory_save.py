from ninjamagic.inventory import collect_dirty_inventory


def test_collect_dirty_inventory_empty():
    items = collect_dirty_inventory()
    assert items == []
