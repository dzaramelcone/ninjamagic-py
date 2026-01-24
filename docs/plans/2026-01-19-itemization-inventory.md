# Itemization Inventory Persistence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist item templates and inventory instances (player + world) with JSONB template specs, inventory locations, and batched dirty saves.

**Architecture:** `items` stores template specs (JSONB dataclass dumps). `inventories` stores item instances + location (container or map), with optional `instance_spec` for per-instance state like count/durability. Item entities carry `ItemTemplateId` + `InventoryId`, and persistence runs via batched upserts in the save loop with dirty flags to avoid frequent writes and duplication.

**Tech Stack:** Python 3.13, FastAPI, esper ECS, Postgres + sqlc, pytest.

**Required skills:** @superpowers:test-driven-development, @superpowers:systematic-debugging, @superpowers:verification-before-completion.

---

### Task 1: Remove Armor.item_rank and use Level for mitigation

**Files:**
- Modify: `ninjamagic/component.py`
- Modify: `ninjamagic/armor.py`
- Modify: `ninjamagic/combat.py`
- Test: `tests/test_armor_level.py`

**Step 1: Write the failing test**
```python
import esper
from ninjamagic.armor import mitigate
from ninjamagic.component import Armor, Level


def test_mitigate_uses_level_component():
    armor = Armor(skill_key="martial_arts", physical_immunity=0.4, magical_immunity=0.0)
    lvl = Level(10)
    out = mitigate(defend_ranks=5, attack_ranks=5, armor=armor, item_level=lvl)
    assert 0.0 < out < 1.0
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_armor_level.py::test_mitigate_uses_level_component -v`
Expected: FAIL (mitigate signature missing item_level).

**Step 3: Write minimal implementation**
```python
# component.py
@dataclass(frozen=True)
class Armor:
    skill_key: str
    physical_immunity: float
    magical_immunity: float

# armor.py
item_mult = contest(item_level, attack_ranks, **kw)

# combat.py
if armor := get_worn_armor(target):
    level = esper.try_component(aid, Level) or Level(0)
    mitigation_factor = mitigate(..., item_level=level)
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_armor_level.py::test_mitigate_uses_level_component -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/component.py ninjamagic/armor.py ninjamagic/combat.py tests/test_armor_level.py
git commit -m "refactor: use item level for armor mitigation"
```

---

### Task 2: Add ItemTemplateId + InventoryId + dirty tags

**Files:**
- Modify: `ninjamagic/component.py`
- Test: `tests/test_inventory_ids.py`

**Step 1: Write the failing test**
```python
from ninjamagic.component import ItemTemplateId, InventoryId


def test_inventory_id_defaults():
    assert InventoryId(0) == 0
    assert ItemTemplateId(0) == 0
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_ids.py::test_inventory_id_defaults -v`
Expected: FAIL (components missing).

**Step 3: Write minimal implementation**
```python
ItemTemplateId = NewType("ItemTemplateId", int)
InventoryId = NewType("InventoryId", int)
class InventoryDirty: ...
class ItemDirty: ...
class Junk: ...
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_ids.py::test_inventory_id_defaults -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/component.py tests/test_inventory_ids.py
git commit -m "feat: add inventory id and dirty tag components"
```

---

### Task 3: Item spec serialization helpers

**Files:**
- Create: `ninjamagic/item_spec.py`
- Modify: `ninjamagic/world/state.py`
- Test: `tests/test_item_spec.py`

**Step 1: Write the failing test**
```python
from ninjamagic.item_spec import dump_item_spec, load_item_spec
from ninjamagic.component import Noun, Weapon


def test_item_spec_roundtrip():
    spec = dump_item_spec([Noun(value="sword"), Weapon(damage=12.0)])
    comps = load_item_spec(spec)
    assert any(isinstance(c, Noun) and c.value == "sword" for c in comps)
    assert any(isinstance(c, Weapon) and c.damage == 12.0 for c in comps)
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_item_spec.py::test_item_spec_roundtrip -v`
Expected: FAIL (module missing).

**Step 3: Write minimal implementation**
```python
# item_spec.py
REGISTRY = {"Noun": Noun, "Weapon": Weapon, ...}

def dump_item_spec(components: list[object]) -> list[dict]:
    # dataclass -> asdict with kind; non-dataclass -> kind only


def load_item_spec(spec: list[dict]) -> list[object]:
    # build instances via kind mapping
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_item_spec.py::test_item_spec_roundtrip -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/item_spec.py ninjamagic/world/state.py tests/test_item_spec.py
git commit -m "feat: add item spec serialization"
```

---

### Task 4: Add items + inventories schema

**Files:**
- Modify: `ninjamagic/sqlc/schema.sql`
- Create: `migrations/003_items_inventories.sql`
- Test: `tests/test_inventory_schema.py`

**Step 1: Write the failing test**
```python
from pathlib import Path


def test_items_migration_exists():
    assert Path("migrations/003_items_inventories.sql").exists()
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_schema.py::test_items_migration_exists -v`
Expected: FAIL (file missing).

**Step 3: Write minimal implementation**
```sql
-- items: id, name, spec jsonb
-- inventories: item_id, owner_id default 0, slot, container_id or map coords, instance_spec
-- container/map CHECK constraint
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_schema.py::test_items_migration_exists -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/sqlc/schema.sql migrations/003_items_inventories.sql tests/test_inventory_schema.py
git commit -m "feat: add items and inventories schema"
```

---

### Task 5: Add sqlc queries + regenerate

**Files:**
- Modify: `ninjamagic/sqlc/query.sql`
- Modify (generated): `ninjamagic/gen/query.py`, `ninjamagic/gen/models.py`
- Test: `tests/test_inventory_queries.py`

**Step 1: Write the failing test**
```python
from ninjamagic.gen.query import AsyncQuerier


def test_inventory_queries_exist():
    assert hasattr(AsyncQuerier, "get_inventories_for_owner")
    assert hasattr(AsyncQuerier, "get_items_by_ids")
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_queries.py::test_inventory_queries_exist -v`
Expected: FAIL (methods missing).

**Step 3: Write minimal implementation**
```sql
-- name: GetInventoriesForOwner :many
SELECT * FROM inventories WHERE owner_id = $1;

-- name: GetInventoriesForMap :many
SELECT * FROM inventories WHERE map_id = $1;

-- name: GetItemsByIds :many
SELECT * FROM items WHERE id = ANY($1::bigint[]);

-- name: UpsertItemByName :one
INSERT INTO items (name, spec) VALUES ($1, $2)
ON CONFLICT (name) DO UPDATE SET spec = EXCLUDED.spec, updated_at = now()
RETURNING id;

-- name: UpsertInventory :one
INSERT INTO inventories (id, owner_id, item_id, slot, container_id, map_id, x, y, instance_spec)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
ON CONFLICT (id) DO UPDATE
SET owner_id = EXCLUDED.owner_id,
    item_id = EXCLUDED.item_id,
    slot = EXCLUDED.slot,
    container_id = EXCLUDED.container_id,
    map_id = EXCLUDED.map_id,
    x = EXCLUDED.x,
    y = EXCLUDED.y,
    instance_spec = EXCLUDED.instance_spec
RETURNING id;

-- name: DeleteInventoryById :exec
DELETE FROM inventories WHERE id = $1;
```
Generate:
```bash
sqlc generate
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_queries.py::test_inventory_queries_exist -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/sqlc/query.sql ninjamagic/gen/query.py ninjamagic/gen/models.py tests/test_inventory_queries.py
git commit -m "feat: add inventory sqlc queries"
```

---

### Task 6: Load inventory + world items

**Files:**
- Create: `ninjamagic/inventory.py`
- Modify: `ninjamagic/conn.py`
- Modify: `ninjamagic/state.py`
- Test: `tests/test_inventory_load.py`

**Step 1: Write the failing test**
```python
from ninjamagic.inventory import hydrate_item_entity


def test_hydrate_item_sets_components():
    entity = hydrate_item_entity(template_name="torch", spec=[{"kind": "Noun", "value": "torch"}])
    assert entity != 0
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_load.py::test_hydrate_item_sets_components -v`
Expected: FAIL (module missing).

**Step 3: Write minimal implementation**
```python
# inventory.py
async def load_world_items(q):
    # fetch inventories by map, hydrate entities, add Transform

async def load_player_inventory(q, owner_id, entity_id):
    # fetch inventories by owner_id, hydrate items, set ContainedBy/Slot

# state.py aopen: load world items once
# conn.py send_init: load player inventory before send_skills
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_load.py::test_hydrate_item_sets_components -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/inventory.py ninjamagic/conn.py ninjamagic/state.py tests/test_inventory_load.py
git commit -m "feat: load inventory and world items"
```

---

### Task 7: Mark dirty inventory on moves

**Files:**
- Modify: `ninjamagic/move.py`
- Modify: `ninjamagic/commands.py`
- Test: `tests/test_inventory_dirty.py`

**Step 1: Write the failing test**
```python
import esper
import ninjamagic.bus as bus
import ninjamagic.move as move
from ninjamagic.component import InventoryDirty


def test_move_entity_marks_dirty():
    eid = esper.create_entity()
    bus.pulse(bus.MoveEntity(source=eid, container=1, slot=""))
    move.process()
    assert esper.has_component(eid, InventoryDirty)
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_dirty.py::test_move_entity_marks_dirty -v`
Expected: FAIL (dirty not set).

**Step 3: Write minimal implementation**
```python
# move.process: add InventoryDirty when MoveEntity or PositionChanged affects items
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_dirty.py::test_move_entity_marks_dirty -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/move.py ninjamagic/commands.py tests/test_inventory_dirty.py
git commit -m "feat: mark dirty inventory on item moves"
```

---

### Task 8: Persist dirty items/inventories in save loop

**Files:**
- Modify: `ninjamagic/main.py`
- Modify: `ninjamagic/inventory.py`
- Test: `tests/test_inventory_save.py`

**Step 1: Write the failing test**
```python
from ninjamagic.inventory import collect_dirty_inventory


def test_collect_dirty_inventory_empty():
    items = collect_dirty_inventory()
    assert items == []
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_save.py::test_collect_dirty_inventory_empty -v`
Expected: FAIL (helper missing).

**Step 3: Write minimal implementation**
```python
# inventory.py
async def save_dirty_inventory(q):
    # upsert items/templates + inventories in one transaction

# main.save(): call save_dirty_inventory before update_character
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_save.py::test_collect_dirty_inventory_empty -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/main.py ninjamagic/inventory.py tests/test_inventory_save.py
git commit -m "feat: persist dirty inventory in save loop"
```

---

### Task 9: Junk cleanup at nightstorm tick

**Files:**
- Modify: `ninjamagic/inventory.py`
- Modify: `ninjamagic/scheduler.py`
- Test: `tests/test_inventory_cleanup.py`

**Step 1: Write the failing test**
```python
import esper
import ninjamagic.bus as bus
import ninjamagic.inventory as inventory
from ninjamagic.component import Junk


def test_junk_cleanup_on_restcheck():
    eid = esper.create_entity(Junk())
    bus.pulse(bus.RestCheck())
    inventory.process()
    assert not esper.entity_exists(eid)
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_cleanup.py::test_junk_cleanup_on_restcheck -v`
Expected: FAIL (cleanup missing).

**Step 3: Write minimal implementation**
```python
# inventory.process: on RestCheck, delete Junk entities and associated inventory rows
# state.py: add inventory.process() in loop
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_cleanup.py::test_junk_cleanup_on_restcheck -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/inventory.py ninjamagic/scheduler.py tests/test_inventory_cleanup.py
git commit -m "feat: cleanup junk items at nightstorm"
```

---

### Task 10: End-to-end inventory integration

**Files:**
- Modify: `tests/test_ws_chat.py`
- Test: `tests/test_inventory_integration.py`

**Step 1: Write the failing test**
```python
# create a fake item in world DB, ensure it loads and can be picked up
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_inventory_integration.py -v`
Expected: FAIL (inventory persistence missing).

**Step 3: Write minimal implementation**
```python
# use inventory load/save helpers in test harness
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_inventory_integration.py -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add tests/test_inventory_integration.py tests/test_ws_chat.py
git commit -m "test: add inventory persistence integration"
```
