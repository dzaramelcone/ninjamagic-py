# D07: Dungeon Terrain Integration

**Effort:** M (4h)
**Phase:** Dungeons (Week 4)
**Dependencies:** T01, D01

---

## Summary

Dungeons use terrain system. Water pools, swamp pockets, magma on deep levels.

---

## Scope

- [ ] Dungeon-specific ChipSet
- [ ] Water pool room variant
- [ ] Swamp pocket room variant
- [ ] Magma room (level 2 only)
- [ ] Terrain hazards active in dungeons

---

## Technical Details

### Dungeon ChipSet

```python
def create_dungeon_chipset(level_eid: EntityId) -> list:
    return [
        (TILE_STONE_FLOOR, level_eid, ord("."), 0.0, 0.1, 0.4, 1.0),
        (TILE_STONE_WALL, level_eid, ord("#"), 0.0, 0.1, 0.3, 1.0),
        (TILE_DUNGEON_WATER_SHALLOW, level_eid, ord("~"), 0.55, 0.6, 0.5, 1.0),
        (TILE_DUNGEON_WATER_DEEP, level_eid, ord("≈"), 0.55, 0.8, 0.4, 1.0),
        (TILE_DUNGEON_SWAMP, level_eid, ord("%"), 0.25, 0.5, 0.3, 1.0),
        (TILE_MAGMA, level_eid, ord("*"), 0.05, 0.9, 0.7, 1.0),
        (TILE_GATE_CLOSED, level_eid, ord("+"), 0.08, 0.3, 0.5, 1.0),
        (TILE_GATE_OPEN, level_eid, ord("'"), 0.08, 0.3, 0.6, 1.0),
    ]
```

### Room Variants

```python
def generate_room_variant(level_eid: EntityId, room_pos: tuple, depth: int):
    variant = RNG.random()

    if variant < 0.15:
        generate_water_pool(level_eid, room_pos)
    elif variant < 0.25:
        generate_swamp_pocket(level_eid, room_pos)
    elif variant < 0.30 and depth >= 2:
        generate_magma_room(level_eid, room_pos)
    else:
        generate_standard_room(level_eid, room_pos)
```

### Water Pool

```python
def generate_water_pool(level_eid: EntityId, room_pos: tuple):
    top = room_pos[0] * TILE_STRIDE_H
    left = room_pos[1] * TILE_STRIDE_W

    # Central pool
    for dy in range(4, 12):
        for dx in range(4, 12):
            dist = abs(dy - 8) + abs(dx - 8)
            if dist <= 4:
                tile = TILE_DUNGEON_WATER_DEEP if dist <= 2 else TILE_DUNGEON_WATER_SHALLOW
                set_tile(level_eid, top + dy, left + dx, tile)
```

---

## Acceptance Criteria

- [ ] Dungeon levels use dungeon ChipSet
- [ ] Water pools appear in some rooms
- [ ] Swamp pockets emit gas (T09)
- [ ] Magma rooms on level 2 deal damage
- [ ] Terrain mechanics work in dungeons
