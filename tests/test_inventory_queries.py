from ninjamagic.gen.query import (
    AsyncQuerier,
    ReplaceInventoriesForMapParams,
    ReplaceInventoriesForOwnerParams,
)


def test_inventory_queries_exist():
    assert hasattr(AsyncQuerier, "get_inventories_for_owner")


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
        levels=[0],
    )
    assert params.keys == ["torch"]


def test_inventory_replace_for_map():
    params = ReplaceInventoriesForMapParams(
        map_id=1,
        ids=[1],
        keys=["torch"],
        slots=[""],
        container_ids=[0],
        map_ids=[1],
        xs=[1],
        ys=[1],
        states=[None],
        levels=[0],
    )
    assert params.map_id == 1
