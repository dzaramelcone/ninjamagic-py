from ninjamagic.gen.query import AsyncQuerier


def test_inventory_queries_exist():
    assert hasattr(AsyncQuerier, "get_inventories_for_owner")
    assert hasattr(AsyncQuerier, "get_items_by_ids")
