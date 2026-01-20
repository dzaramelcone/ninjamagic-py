import pytest
import esper
import sqlalchemy
from psycopg.types.json import Json

import ninjamagic.bus as bus
import ninjamagic.inventory as inventory
import ninjamagic.move as move
from ninjamagic.component import ContainedBy, InventoryId, Noun, OwnerId, Slot, Transform
from ninjamagic.db import get_repository_factory
from ninjamagic.gen.query import UpsertInventoryParams
from ninjamagic.world.state import DEMO


async def _ensure_inventory_schema(q) -> None:
    await q._conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS citext"))
    await q._conn.execute(
        sqlalchemy.text(
            """
            CREATE TABLE IF NOT EXISTS items (
                id BIGSERIAL PRIMARY KEY,
                name CITEXT NOT NULL,
                spec JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (name)
            )
            """
        )
    )
    await q._conn.execute(
        sqlalchemy.text(
            """
            CREATE TABLE IF NOT EXISTS inventories (
                id BIGSERIAL PRIMARY KEY,
                owner_id BIGINT NOT NULL DEFAULT 0,
                item_id BIGINT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                slot TEXT NOT NULL DEFAULT '',
                container_id BIGINT REFERENCES inventories(id) ON DELETE CASCADE,
                map_id INTEGER,
                x INTEGER,
                y INTEGER,
                instance_spec JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CHECK (
                    (container_id IS NOT NULL AND map_id IS NULL AND x IS NULL AND y IS NULL)
                    OR
                    (container_id IS NULL AND map_id IS NOT NULL AND x IS NOT NULL AND y IS NOT NULL)
                )
            )
            """
        )
    )
    await q._conn.execute(
        sqlalchemy.text(
            "CREATE INDEX IF NOT EXISTS idx_inventories_map ON inventories(map_id)"
        )
    )


@pytest.mark.asyncio
async def test_inventory_world_item_load_and_pickup():
    inv_id = 900001
    spec = [{"kind": "Noun", "value": "torch"}]

    async with get_repository_factory() as q:
        await _ensure_inventory_schema(q)
        await q.delete_inventory_by_id(id=inv_id)
        item_id = await q.upsert_item_by_name(
            name="integration-torch",
            spec=Json(spec),
        )
        await q.upsert_inventory(
            UpsertInventoryParams(
                id=inv_id,
                owner_id=0,
                item_id=item_id,
                slot="",
                container_id=None,
                map_id=int(DEMO),
                x=1,
                y=1,
                instance_spec=None,
            )
        )
        await inventory.load_world_items(q)

    item_entity = next(
        eid
        for eid, inv in esper.get_component(InventoryId)
        if int(inv) == inv_id
    )
    loc = esper.component_for_entity(item_entity, Transform)
    noun = esper.component_for_entity(item_entity, Noun)
    assert loc.map_id == DEMO
    assert noun.value == "torch"

    player = esper.create_entity()
    esper.add_component(player, OwnerId(42))
    bus.pulse(bus.MoveEntity(source=item_entity, container=player, slot=Slot.RIGHT_HAND))
    move.process()
    assert esper.component_for_entity(item_entity, ContainedBy) == player

    esper.delete_entity(item_entity)
    esper.delete_entity(player)
    bus.clear()
    esper.clear_dead_entities()

    async with get_repository_factory() as q:
        await q.delete_inventory_by_id(id=inv_id)
