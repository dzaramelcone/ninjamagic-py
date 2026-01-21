from ninjamagic.gen.query import AsyncQuerier, ReplaceInventoriesForOwnerParams


def test_inventory_queries_exist():
    assert hasattr(AsyncQuerier, "get_inventories_for_owner")
    assert hasattr(AsyncQuerier, "get_items_by_ids")


def test_inventory_replace_uses_key_and_state():
    params = ReplaceInventoriesForOwnerParams(
        owner_id=1,
        ids=[1],
        owner_ids=[1],
        keys=["torch"],
        slots=[""],
        container_ids=[0],
        map_ids=[-1],
        xs=[-1],
        ys=[-1],
        states=[None],
    )
    assert params.keys == ["torch"]
