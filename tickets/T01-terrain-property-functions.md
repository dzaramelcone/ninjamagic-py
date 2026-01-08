# T01: Terrain Property Functions

**Effort:** S (2h)
**Phase:** Terrain (Week 1)
**Dependencies:** None

---

## Summary

Terrain properties as functions, not data. Tile IDs are bytes. Properties are derived via O(1) lookups.

---

## Design

### Why Functions?

Tiles are bytes (0-255) stored in chunks. Millions of them. We can't attach a dataclass to each tile - too much memory, too slow.

Instead: property sets. `is_walkable(tile_id)` checks membership in a frozenset. O(1), tiny memory footprint.

### Property Categories

**Boolean properties** (set membership):
- `is_walkable` - can entities stand here?
- `blocks_los` - does this block line of sight?
- `is_flammable` - can fire spread here?
- `is_water` - water mechanics apply?
- `emits_gas` - spawns gas over time?
- `is_damaging` - hurts entities standing here?

**Parameterized properties** (dict lookup):
- `movement_cost(tile_id)` - how slow? (default 1.0)
- `burns_to(tile_id)` - what does this become when burned? (None if not flammable)
- `damage_per_tick(tile_id)` - how much damage? (0.0 if safe)
- `water_depth(tile_id)` - 0/1/2 for none/shallow/deep

### Tile ID Ranges

Organize IDs by category for sanity:
- 0-9: Core overworld (ground, wall, grass, water)
- 10-19: Dungeon structure (stone, gates)
- 20-29: Hazards (swamp, magma, chasm, bridge)

### Integration

Replace hardcoded checks throughout codebase:
- `can_enter()` → `is_walkable()`
- Frontend `isOpaque()` → `blocks_los()`

---

## Acceptance Criteria

- [ ] Tile ID constants defined
- [ ] Property functions for all terrain behaviors
- [ ] O(1) lookup performance
- [ ] `can_enter()` uses `is_walkable()`
- [ ] Existing gameplay unchanged
