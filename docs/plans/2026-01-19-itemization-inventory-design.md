# Itemization Inventory Design

**Goal:** Persist item templates and inventory instances (player + world), with minimal schema and JSONB template specs, while avoiding frequent writes and duplication.

## Architecture
- Item templates live in `items` with a `spec` JSONB dump of component dataclasses (templates are the primary definition).
- Inventory instances live in `inventories` referencing templates via `item_id`, with optional `instance_spec` JSONB for per-instance state (durability/charges/custom name/count).
- World items persist via inventory rows with `(map_id, x, y)` and no `container_id`.
- Contained items persist via `container_id` and no map coordinates.
- A CHECK constraint enforces container-or-map (never both).

## Components + Data Flow
- Item entities carry `ItemId` (DB id), separate from ECS entity ids.
- Load: fetch inventories by owner (player) and by map for world items; fetch referenced item templates; hydrate ECS entities from template `spec` JSONB and overlay `instance_spec` if present.
- Save: only persist dirty items/inventories, batching upserts inside a single transaction to avoid duplication. Inventory rows mutate on `MoveEntity` (container/slot) or `PositionChanged` (map/x/y).
- Cleanup: on nightstorm tick (06:00), delete entities tagged junk/expired and remove their inventory rows.

## Error Handling
- Missing template rows for inventory entries: log and drop the inventory row.
- Invalid JSONB spec: log and skip creating the entity.
- Invalid container/map combos: log and drop the inventory row.

## Testing
- JSONB spec serialization and rehydration for item templates.
- Inventory constraint enforcement (container vs map).
- Dirty-save batching (only changed rows persisted).
- Junk cleanup on nightstorm tick.
- Integration: login loads inventory + world items; drop/pickup/give updates inventories without duplicates.
