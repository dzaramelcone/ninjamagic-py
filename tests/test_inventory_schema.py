from pathlib import Path

import pytest
import sqlalchemy

from ninjamagic import db


def test_inventories_migration_exists():
    assert Path("migrations/004_inventories.sql").exists()


@pytest.mark.asyncio
async def test_inventory_schema_key_state_fk():
    async with db.get_repository_factory() as q:
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
