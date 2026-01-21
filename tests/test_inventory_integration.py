import esper
import httpx
import pytest

import ninjamagic.bus as bus
import ninjamagic.move as move
from ninjamagic.component import ContainedBy, ItemKey, OwnerId, Slot, Transform
from ninjamagic import db
from ninjamagic.gen.query import ReplaceInventoriesForMapParams
from ninjamagic.main import app
from ninjamagic.world import state as world_state


@pytest.mark.asyncio
async def test_inventory_world_item_load_and_pickup():
    inv_id = 900001

    async with db.get_repository_factory() as q:
        await q.delete_inventory_by_id(id=inv_id)
        map_id = world_state.build_nowhere()
        await q.replace_inventories_for_map(
            ReplaceInventoriesForMapParams(
                map_id=int(map_id),
                ids=[inv_id],
                keys=["torch"],
                slots=[""],
                container_ids=[0],
                map_ids=[int(map_id)],
                xs=[1],
                ys=[1],
                states=[None],
                levels=[0],
            )
        )
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/")

    # Find the torch by its ItemKey and Transform
    item_entity = next(
        eid
        for eid, (key, loc) in esper.get_components(ItemKey, Transform)
        if key.key == "torch" and loc.map_id == map_id and loc.x == 1 and loc.y == 1
    )
    loc = esper.component_for_entity(item_entity, Transform)
    item_key = esper.component_for_entity(item_entity, ItemKey)
    assert loc.map_id == map_id
    assert item_key.key == "torch"

    player = esper.create_entity()
    esper.add_component(player, OwnerId(42))
    bus.pulse(bus.MoveEntity(source=item_entity, container=player, slot=Slot.RIGHT_HAND))
    move.process()
    assert esper.component_for_entity(item_entity, ContainedBy) == player

    esper.delete_entity(item_entity)
    esper.delete_entity(player)
    bus.clear()
    esper.clear_dead_entities()

    async with db.get_repository_factory() as q:
        await q.delete_inventory_by_id(id=inv_id)
