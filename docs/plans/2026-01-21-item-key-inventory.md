# Item Key Inventory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace item template rows with a keyed inventory table that stores only location, template key, and per-instance state.

**Architecture:** Keep a module-level item template dict in `inventory.py`. Persist `key` + `state` in `inventories`. At load, attach template components based on key and optional instance state. At save, write location + key + state (no items table).

**Tech Stack:** PostgreSQL schema/migrations, sqlc queries, Python ECS (esper), pytest.

### Task 1: Update schema + migration for keyed inventories

**Files:**
- Modify: `ninjamagic/sqlc/schema.sql`
- Modify: `migrations/004_inventory_owner_constraint.sql`
- Modify: `ninjamagic/sqlc/query.sql`
- Regenerate: `ninjamagic/gen/query.py`

**Step 1: Write the failing test**

```python
import pytest
import sqlalchemy
from ninjamagic.db import get_repository_factory


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
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_inventory_schema.py::test_inventory_schema_key_state_fk -v`
Expected: FAIL because schema still requires item_id and owner_id not null.

**Step 3: Write minimal implementation**

- Drop `items` table usage from inventories schema.
- Add `key TEXT NOT NULL`.
- Make `owner_id BIGINT NULL REFERENCES characters(id) ON DELETE CASCADE`.
- Rename `instance_spec` to `state` (JSONB).
- Update `inventories_location_check` to allow `owner_id IS NULL` for map/world rows.

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_inventory_schema.py::test_inventory_schema_key_state_fk -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add ninjamagic/sqlc/schema.sql migrations/004_inventory_owner_constraint.sql

git commit -m "feat: key inventory schema with nullable owner_id"
```

### Task 2: Update sqlc queries and types

**Files:**
- Modify: `ninjamagic/sqlc/query.sql`
- Regenerate: `ninjamagic/gen/query.py`
- Modify: `ninjamagic/inventory.py`
- Test: `tests/test_inventory_queries.py`

**Step 1: Write the failing test**

```python
from ninjamagic.gen.query import ReplaceInventoriesForOwnerParams


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
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_inventory_queries.py::test_inventory_replace_uses_key_and_state -v`
Expected: FAIL because params don't include keys/states yet.

**Step 3: Write minimal implementation**

- Update ReplaceInventoriesForOwner to use `keys` + `states` columns.
- Update `inventories` SQL queries to return `key` + `state`.
- Regenerate sqlc output.
- Update inventory persistence to use `ItemKey` instead of `ItemTemplateId`.

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_inventory_queries.py::test_inventory_replace_uses_key_and_state -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add ninjamagic/sqlc/query.sql ninjamagic/gen/query.py tests/test_inventory_queries.py ninjamagic/inventory.py

git commit -m "refactor: save inventories with key/state"
```

### Task 3: Update inventory load/save for item keys

**Files:**
- Modify: `ninjamagic/inventory.py`
- Modify: `ninjamagic/component.py`
- Test: `tests/test_inventory_load.py`
- Test: `tests/test_inventory_save.py`

**Step 1: Write the failing test**

```python
from ninjamagic.component import ItemKey


def test_item_key_component_exists():
    assert ItemKey("torch")
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_inventory_load.py::test_item_key_component_exists -v`
Expected: FAIL because ItemKey component is missing.

**Step 3: Write minimal implementation**

- Add `ItemKey = NewType("ItemKey", str)` (or dataclass) to `component.py`.
- Add module-level `ITEM_TEMPLATES` dict in `inventory.py` keyed by `ItemKey`.
- Load: attach `ItemKey` to entity; add template components from dict.
- Save: require `ItemKey` and write key to DB. State remains `None` for now.

**Step 4: Run tests**

Run: `uv run python -m pytest tests/test_inventory_load.py tests/test_inventory_save.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add ninjamagic/component.py ninjamagic/inventory.py tests/test_inventory_load.py tests/test_inventory_save.py

git commit -m "feat: persist inventory item keys"
```

### Task 4: World item bulk replace

**Files:**
- Modify: `ninjamagic/sqlc/query.sql`
- Regenerate: `ninjamagic/gen/query.py`
- Modify: `ninjamagic/inventory.py`
- Test: `tests/test_inventory_queries.py`

**Step 1: Write the failing test**

```python
from ninjamagic.gen.query import ReplaceInventoriesForMapParams


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
    )
    assert params.map_id == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_inventory_queries.py::test_inventory_replace_for_map -v`
Expected: FAIL because query/params don’t exist yet.

**Step 3: Write minimal implementation**

- Add `ReplaceInventoriesForMap` query that deletes rows where `owner_id IS NULL AND map_id = $1` and inserts new ones.
- Update inventory save path for world items (separate function).

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_inventory_queries.py::test_inventory_replace_for_map -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add ninjamagic/sqlc/query.sql ninjamagic/gen/query.py tests/test_inventory_queries.py ninjamagic/inventory.py

git commit -m "feat: bulk replace world inventories"
```

### Task 5: Inventory integration tests

**Files:**
- Modify: `tests/test_inventory_integration.py`
- Test: `tests/test_inventory_integration.py`

**Step 1: Update test fixtures**

- Insert rows with `key` instead of `item_id`.
- Update asserts to check `ItemKey`.

**Step 2: Run test**

Run: `uv run python -m pytest tests/test_inventory_integration.py -v`
Expected: PASS (server not required for ASGI transport test).

**Step 3: Commit**

```bash
git add tests/test_inventory_integration.py

git commit -m "test: inventory integration for item keys"
```
