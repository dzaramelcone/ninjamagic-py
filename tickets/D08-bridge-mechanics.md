# D08: Bridge Mechanics

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** T01, T03

---

## Summary

Burnable rope bridges over chasms. Tactical positioning + fire creates permanent map changes.

---

## Scope

- [ ] `TILE_BRIDGE` terrain type (walkable, flammable)
- [ ] `TILE_CHASM` terrain type (not walkable, not blocking LOS)
- [ ] Bridges burn and collapse when ignited
- [ ] Bridge placement during dungeon generation

---

## Technical Details

### Terrain Constants

```python
TILE_BRIDGE = 25
TILE_CHASM = 26

WALKABLE |= {TILE_BRIDGE}
FLAMMABLE |= {TILE_BRIDGE}
BURNS_TO[TILE_BRIDGE] = TILE_CHASM
```

### Bridge Corridor

```python
def place_bridge_corridor(level_eid: EntityId, corridor_pos: tuple):
    top = corridor_pos[0] * TILE_STRIDE_H + 6
    left = corridor_pos[1] * TILE_STRIDE_W

    for dy in range(4):
        for dx in range(16):
            y, x = top + dy, left + dx
            if 6 <= dx <= 9:
                set_tile(level_eid, y, x, TILE_BRIDGE)
            else:
                set_tile(level_eid, y, x, TILE_CHASM)
```

---

## Tactical Implications

- Cut off pursuit by burning bridge behind you
- Trap enemies on far side
- Permanent map alteration - no going back

---

## Acceptance Criteria

- [ ] Bridge tiles are walkable and flammable
- [ ] Chasm tiles block movement but not LOS
- [ ] Fire on bridge causes collapse to chasm
- [ ] Bridges placed in dungeon corridors (level 2+)
