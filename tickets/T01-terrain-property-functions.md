# T01: Terrain Property Functions

**Effort:** S (2h)
**Phase:** Terrain (Week 1)
**Dependencies:** None

---

## Summary

Create lightweight terrain property functions. Tile IDs are bytes (0-255). Properties are derived via functions, not stored in heavy dataclasses.

---

## Current State

- Tiles are bytes (0-255) in 16x16 chunks (`Chips`)
- `can_enter()` checks if tile in `{1, 3}` - hardcoded set
- `isOpaque()` on frontend checks hardcoded char list
- No terrain properties (flammable, water, movement cost, etc.)

---

## Scope

- [ ] Create `ninjamagic/terrain.py` with property functions
- [ ] Define tile ID constants for all terrain types
- [ ] Property functions: `is_walkable(tile_id)`, `blocks_los(tile_id)`, etc.
- [ ] Update `can_enter()` to use `is_walkable()`
- [ ] Use sets/ranges for O(1) lookup

---

## Technical Details

### Tile ID Constants

```python
# terrain.py
# Core tiles (0-9)
TILE_VOID = 0
TILE_GROUND = 1
TILE_WALL = 2
TILE_WATER_SHALLOW = 3
TILE_GRASS = 4
TILE_DRY_GRASS = 5
TILE_BURNED = 6
TILE_MUD = 7

# Dungeon tiles (10-19)
TILE_STONE_FLOOR = 10
TILE_STONE_WALL = 11
TILE_GATE_CLOSED = 12
TILE_GATE_OPEN = 13

# Hazard tiles (20-29)
TILE_DUNGEON_SWAMP = 20
TILE_DUNGEON_WATER_SHALLOW = 21
TILE_DUNGEON_WATER_DEEP = 22
TILE_MAGMA = 23
TILE_FIRE = 24
TILE_BRIDGE = 25
TILE_CHASM = 26
```

### Property Sets (O(1) Lookup)

```python
# terrain.py
WALKABLE: frozenset[int] = frozenset({
    TILE_GROUND, TILE_WATER_SHALLOW, TILE_GRASS, TILE_DRY_GRASS,
    TILE_BURNED, TILE_MUD, TILE_STONE_FLOOR, TILE_GATE_OPEN,
    TILE_DUNGEON_SWAMP, TILE_DUNGEON_WATER_SHALLOW, TILE_DUNGEON_WATER_DEEP,
    TILE_BRIDGE,
})

BLOCKS_LOS: frozenset[int] = frozenset({
    TILE_WALL, TILE_STONE_WALL,
})

FLAMMABLE: frozenset[int] = frozenset({
    TILE_GRASS, TILE_DRY_GRASS, TILE_BRIDGE,
})

EMITS_GAS: frozenset[int] = frozenset({
    TILE_DUNGEON_SWAMP,
})

WATER: frozenset[int] = frozenset({
    TILE_WATER_SHALLOW, TILE_DUNGEON_WATER_SHALLOW, TILE_DUNGEON_WATER_DEEP,
})

DAMAGING: frozenset[int] = frozenset({
    TILE_MAGMA, TILE_FIRE,
})
```

### Property Functions

```python
def is_walkable(tile_id: int) -> bool:
    return tile_id in WALKABLE

def blocks_los(tile_id: int) -> bool:
    return tile_id in BLOCKS_LOS

def is_flammable(tile_id: int) -> bool:
    return tile_id in FLAMMABLE

def emits_gas(tile_id: int) -> bool:
    return tile_id in EMITS_GAS

def is_water(tile_id: int) -> bool:
    return tile_id in WATER

def is_damaging(tile_id: int) -> bool:
    return tile_id in DAMAGING
```

### Parameterized Functions

```python
MOVEMENT_COST: dict[int, float] = {
    TILE_WATER_SHALLOW: 1.5,
    TILE_MUD: 1.3,
    TILE_DUNGEON_SWAMP: 1.4,
    TILE_DUNGEON_WATER_DEEP: 2.0,
}

def movement_cost(tile_id: int) -> float:
    return MOVEMENT_COST.get(tile_id, 1.0)

BURNS_TO: dict[int, int] = {
    TILE_GRASS: TILE_BURNED,
    TILE_DRY_GRASS: TILE_BURNED,
    TILE_BRIDGE: TILE_CHASM,
}

def burns_to(tile_id: int) -> int | None:
    return BURNS_TO.get(tile_id)

DAMAGE_PER_TICK: dict[int, float] = {
    TILE_MAGMA: 20.0,
    TILE_FIRE: 5.0,
}

def damage_per_tick(tile_id: int) -> float:
    return DAMAGE_PER_TICK.get(tile_id, 0.0)
```

---

## Files

- `ninjamagic/terrain.py` (new)
- `ninjamagic/world/state.py` (update `can_enter`)

---

## Acceptance Criteria

- [ ] Tile ID constants defined for all terrain types
- [ ] Property sets for O(1) boolean lookups
- [ ] Property functions for parameterized lookups
- [ ] `can_enter()` uses `is_walkable()`
- [ ] Existing gameplay unchanged
- [ ] Tests pass

---

## Design Notes

**Why not a dataclass?**
Terrain is massive. Using sets and dicts with byte keys is faster (O(1)), smaller (no object overhead), and scalable (works for millions of tiles).
