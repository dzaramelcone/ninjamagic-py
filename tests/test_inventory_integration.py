import esper
import httpx
import pytest

import ninjamagic.bus as bus
import ninjamagic.move as move
from ninjamagic.component import ContainedBy, ItemKey, OwnerId, Slot, Transform
from ninjamagic import db
from ninjamagic.gen.query import ReplaceInventoriesForMapParams
from ninjamagic.inventory import create_item, load_player_inventory, save_player_inventory
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
                eids=[inv_id],
                keys=["torch"],
                slots=[""],
                container_eids=[0],
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


@pytest.mark.asyncio
async def test_nested_container_save_and_load():
    """Player wears backpack, backpack contains cookpot, cookpot contains leek."""

    # Create a test character in the database
    async with db.get_repository_factory() as q:
        result = await q.create_character(owner_id=999999, name="TestNester", pronoun="they")
        assert result
        char_id = result.id

    # Create player entity
    player = esper.create_entity()
    esper.add_component(player, OwnerId(char_id))

    # Create items: backpack → cookpot → leek
    backpack = create_item("backpack")
    cookpot = create_item("cookpot")
    leek = create_item("leek")

    # Set up containment hierarchy
    esper.add_component(backpack, player, ContainedBy)
    esper.add_component(backpack, Slot.BACK)
    esper.add_component(cookpot, backpack, ContainedBy)
    esper.add_component(cookpot, Slot.ANY)
    esper.add_component(leek, cookpot, ContainedBy)
    esper.add_component(leek, Slot.ANY)

    # Save to database
    async with db.get_repository_factory() as q:
        await save_player_inventory(q, owner_id=char_id, owner_entity=player)

    # Clear all entities
    esper.delete_entity(leek)
    esper.delete_entity(cookpot)
    esper.delete_entity(backpack)
    esper.delete_entity(player)
    esper.clear_dead_entities()

    # Create fresh player entity for loading
    player2 = esper.create_entity()
    assert player != player2
    esper.add_component(player2, OwnerId(char_id))

    # Load from database
    async with db.get_repository_factory() as q:
        await load_player_inventory(q, owner_id=char_id, entity_id=player2)

    # Find loaded items by their keys
    loaded_backpack = next(
        eid for eid, key in esper.get_component(ItemKey) if key.key == "backpack"
    )
    loaded_cookpot = next(
        eid for eid, key in esper.get_component(ItemKey) if key.key == "cookpot"
    )
    loaded_leek = next(
        eid for eid, key in esper.get_component(ItemKey) if key.key == "leek"
    )

    # Verify containment hierarchy is restored
    assert esper.component_for_entity(loaded_backpack, ContainedBy) == player2
    assert esper.component_for_entity(loaded_cookpot, ContainedBy) == loaded_backpack
    assert esper.component_for_entity(loaded_leek, ContainedBy) == loaded_cookpot

    # Cleanup
    esper.delete_entity(loaded_leek)
    esper.delete_entity(loaded_cookpot)
    esper.delete_entity(loaded_backpack)
    esper.delete_entity(player2)
    esper.clear_dead_entities()

    # Cleanup database (cascade delete handles inventories)
    async with db.get_repository_factory() as q:
        await q.delete_character(id=char_id)
