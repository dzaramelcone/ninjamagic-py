from typing import get_args

import esper
import httpx
import pytest

import ninjamagic.bus as bus
import ninjamagic.move as move
from ninjamagic import db
from ninjamagic.component import Chips, ContainedBy, Food, Glyph, ItemKey, Noun, OwnerId, Slot, Transform
from ninjamagic.util import PLURAL
from ninjamagic.gen.query import ReplaceInventoriesForMapParams
from ninjamagic.inventory import (
    State,
    create_item,
    load_map_inventory,
    load_player_inventory,
    save_map_inventory,
    save_player_inventory,
)
from ninjamagic.main import app
from ninjamagic.world import state as world_state


def test_state_component_types_are_frozen_and_eq():
    """All component types in State must be frozen dataclasses with eq=True."""
    for name, field_info in State.model_fields.items():
        component_type = next(a for a in get_args(field_info.annotation) if a is not type(None))
        params = getattr(component_type, "__dataclass_params__", None)
        assert params, f"State.{name} type {component_type.__name__} must be a dataclass"
        assert params.frozen, f"State.{name} type {component_type.__name__} must be frozen"
        assert params.eq, f"State.{name} type {component_type.__name__} must have eq=True"


@pytest.mark.asyncio
async def test_inventory_world_item_load_and_pickup():
    inv_id = 900001
    map_id = world_state.build_nowhere()

    async with db.get_repository_factory() as q:
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

    player = esper.create_entity()
    esper.add_component(player, OwnerId(42))
    bus.pulse(bus.MoveEntity(source=item_entity, container=player, slot=Slot.RIGHT_HAND))
    move.process()
    assert esper.component_for_entity(item_entity, ContainedBy) == player


@pytest.mark.asyncio
async def test_nested_container_save_and_load():
    """Player wears backpack, backpack contains cookpot, cookpot contains meal."""

    # Create a test character in the database
    async with db.get_repository_factory() as q:
        result = await q.create_character(owner_id=999999, name="TestNester", pronoun="they")
        assert result
        char_id = result.id

    # Create player entity
    player = esper.create_entity()
    esper.add_component(player, OwnerId(char_id))

    # Create items: backpack → cookpot → meal
    backpack = create_item("backpack", transform=Transform(map_id=0, y=0, x=0), level=0)
    cookpot = create_item("cookpot", transform=Transform(map_id=0, y=0, x=0), level=0)
    meal = create_item("meal", transform=Transform(map_id=0, y=0, x=0), level=0)

    # Set up containment hierarchy
    esper.add_component(backpack, player, ContainedBy)
    esper.add_component(backpack, Slot.BACK)
    esper.add_component(cookpot, backpack, ContainedBy)
    esper.add_component(cookpot, Slot.ANY)
    esper.add_component(meal, cookpot, ContainedBy)
    esper.add_component(meal, Slot.ANY)

    # Save to database
    async with db.get_repository_factory() as q:
        await save_player_inventory(q, owner_id=char_id, owner_entity=player)

    # Clear all entities
    esper.delete_entity(meal)
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
    loaded_meal = next(
        eid for eid, key in esper.get_component(ItemKey) if key.key == "meal"
    )

    # Verify containment hierarchy is restored
    assert esper.component_for_entity(loaded_backpack, ContainedBy) == player2
    assert esper.component_for_entity(loaded_cookpot, ContainedBy) == loaded_backpack
    assert esper.component_for_entity(loaded_meal, ContainedBy) == loaded_cookpot


@pytest.mark.asyncio
async def test_item_state_persistence():
    """Item with custom state (Noun, Food) should persist through save/load."""
    # Create test character
    async with db.get_repository_factory() as q:
        result = await q.create_character(owner_id=999998, name="TestStateful", pronoun="they")
        char_id = result.id

    # Create player entity
    player = esper.create_entity()
    esper.add_component(player, OwnerId(char_id))

    # Create forage item with custom Noun (differs from template "forage")
    custom_noun = Noun(adjective="fresh", value="walnuts", num=PLURAL)
    forage = create_item(
        "forage",
        custom_noun,
        transform=Transform(map_id=0, y=0, x=0),
        level=5,
    )
    esper.add_component(forage, player, ContainedBy)
    esper.add_component(forage, Slot.ANY)

    # Create meal with custom Food count (differs from template count=1)
    custom_food = Food(count=3)
    meal = create_item(
        "meal",
        custom_food,
        transform=Transform(map_id=0, y=0, x=0),
        level=2,
    )
    esper.add_component(meal, player, ContainedBy)
    esper.add_component(meal, Slot.ANY)

    # Save to database
    async with db.get_repository_factory() as q:
        await save_player_inventory(q, owner_id=char_id, owner_entity=player)

    # Clear all entities
    esper.delete_entity(meal)
    esper.delete_entity(forage)
    esper.delete_entity(player)
    esper.clear_dead_entities()

    # Create fresh player for loading
    player2 = esper.create_entity()
    esper.add_component(player2, OwnerId(char_id))

    # Load from database
    async with db.get_repository_factory() as q:
        await load_player_inventory(q, owner_id=char_id, entity_id=player2)

    # Find loaded items
    loaded_forage = next(
        eid for eid, key in esper.get_component(ItemKey) if key.key == "forage"
    )
    loaded_meal = next(
        eid for eid, key in esper.get_component(ItemKey) if key.key == "meal"
    )

    # Assert Noun state persisted
    loaded_noun = esper.component_for_entity(loaded_forage, Noun)
    assert loaded_noun.adjective == "fresh"
    assert loaded_noun.value == "walnuts"
    assert loaded_noun.num == PLURAL

    # Assert Food state persisted
    loaded_food = esper.component_for_entity(loaded_meal, Food)
    assert loaded_food.count == 3


@pytest.mark.asyncio
async def test_map_item_state_persistence():
    """World item with custom state (Noun, Glyph) should persist through save/load."""
    # Use a real map from world_state
    map_id = world_state.build_nowhere()
    assert esper.has_component(map_id, Chips)

    # Create prop item with custom Noun and Glyph (like a lily pad)
    custom_noun = Noun(value="lily pad")
    custom_glyph = Glyph(char="ო", h=0.33, s=0.6, v=0.6)
    prop = create_item(
        "prop",
        custom_noun,
        custom_glyph,
        transform=Transform(map_id=map_id, y=5, x=5),
        level=0,
    )

    # Create forage with custom Noun
    custom_forage_noun = Noun(value="chive")
    forage = create_item(
        "forage",
        custom_forage_noun,
        transform=Transform(map_id=map_id, y=6, x=6),
        level=3,
    )

    # Save to database
    async with db.get_repository_factory() as q:
        await save_map_inventory(q, map_id=map_id)

    # Clear item entities (keep map)
    esper.delete_entity(prop)
    esper.delete_entity(forage)
    esper.clear_dead_entities()

    # Verify items are gone
    assert not any(key.key == "prop" for _, key in esper.get_component(ItemKey))
    assert not any(key.key == "forage" for _, key in esper.get_component(ItemKey))

    # Load from database
    async with db.get_repository_factory() as q:
        await load_map_inventory(q)

    # Find loaded items by key AND position (to avoid picking up leftovers)
    loaded_prop = next(
        eid
        for eid, (key, t) in esper.get_components(ItemKey, Transform)
        if key.key == "prop" and t.map_id == map_id and t.x == 5 and t.y == 5
    )
    loaded_forage = next(
        eid
        for eid, (key, t) in esper.get_components(ItemKey, Transform)
        if key.key == "forage" and t.map_id == map_id and t.x == 6 and t.y == 6
    )

    # Assert Noun state persisted for prop
    loaded_noun = esper.component_for_entity(loaded_prop, Noun)
    assert loaded_noun.value == "lily pad"

    # Assert Glyph state persisted for prop
    loaded_glyph = esper.component_for_entity(loaded_prop, Glyph)
    assert loaded_glyph.char == "ო"
    assert loaded_glyph.h == pytest.approx(0.33)
    assert loaded_glyph.s == pytest.approx(0.6)
    assert loaded_glyph.v == pytest.approx(0.6)

    # Assert Noun state persisted for forage
    loaded_forage_noun = esper.component_for_entity(loaded_forage, Noun)
    assert loaded_forage_noun.value == "chive"

    # Assert Transform persisted
    loaded_transform = esper.component_for_entity(loaded_prop, Transform)
    assert loaded_transform.map_id == map_id
    assert loaded_transform.x == 5
    assert loaded_transform.y == 5
