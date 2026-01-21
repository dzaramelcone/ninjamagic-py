from pathlib import Path

import pytest
import sqlalchemy

from ninjamagic.db import get_repository_factory


def test_items_migration_exists():
    assert Path("migrations/003_items_inventories.sql").exists()


def test_inventory_owner_constraint_migration_exists():
    assert Path("migrations/004_inventory_owner_constraint.sql").exists()


def test_key_inventory_migration_exists():
    assert Path("migrations/005_key_inventory.sql").exists()


@pytest.mark.asyncio
async def test_inventory_schema_key_state_fk():
    async with get_repository_factory() as q:
        await q._conn.execute(sqlalchemy.text("SELECT 1"))
        # should be able to insert a world item with NULL owner_id
        await q._conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO inventories (key, owner_id, map_id, x, y, slot)
                VALUES ('torch', NULL, 1, 1, 1, '')
                """
            )
        )
