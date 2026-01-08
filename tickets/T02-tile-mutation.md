# T02: Tile Mutation

**Effort:** S (2h)
**Phase:** Terrain (Week 1)
**Dependencies:** T01

---

## Summary

Create system for changing tile types at runtime. Fire burns grass to ash, water freezes, etc.

---

## Current State

- Tiles stored in `Chips` component (bytearray grid)
- No mechanism to change tiles after generation
- `set_tile()` function doesn't exist

---

## Scope

- [ ] `MutateTile` signal for tile changes
- [ ] `set_tile()` helper function
- [ ] Tile mutation processor
- [ ] Network sync for tile changes
- [ ] ChipSet updates if needed

---

## Technical Details

### Signal

```python
# bus.py
@signal(frozen=True, slots=True, kw_only=True)
class MutateTile(Signal):
    map_id: int
    y: int
    x: int
    new_tile: int
```

### set_tile Helper

```python
# world/state.py
def set_tile(*, map_id: int, y: int, x: int, tile_id: int) -> bool:
    """Change a tile at position. Returns True if successful."""
    chips = esper.try_component(map_id, Chips)
    if not chips:
        return False

    chunk_y = y // TILE_STRIDE_H
    chunk_x = x // TILE_STRIDE_W
    chunk_key = (chunk_y, chunk_x)

    grid = chips.dict.get(chunk_key)
    if not grid:
        return False

    local_y = y % TILE_STRIDE_H
    local_x = x % TILE_STRIDE_W
    idx = local_y * TILE_STRIDE_W + local_x

    grid[idx] = tile_id
    return True
```

### Mutation Processor

Runs before `move` in system loop - tile changes can invalidate movement state.

```python
# mutation.py
def process():
    for sig in bus.iter(bus.MutateTile):
        # Validate: if tile becomes unwalkable, handle entities on it
        # (push them off, damage them, or block the mutation)
        if not _validate_mutation(sig):
            continue

        success = set_tile(
            map_id=sig.map_id,
            y=sig.y,
            x=sig.x,
            tile_id=sig.new_tile,
        )
        if success:
            bus.pulse(bus.TileChanged(
                map_id=sig.map_id,
                y=sig.y,
                x=sig.x,
                tile_id=sig.new_tile,
            ))
```

### Validation

When a tile becomes unwalkable with an entity on it:
- **Bridge → chasm**: Entity falls (damage + move to level below or death)
- **Ground → wall**: Block mutation (shouldn't happen organically)
- **Water shallow → water deep**: Entity starts drowning

### Network Sync

```python
# outbox.py
def encode_tile_change(sig: TileChanged) -> bytes:
    """Packet: 10 bytes - map_id(4) + y(2) + x(2) + tile(1) + msg_type(1)"""
    return struct.pack(">BIHHB", MSG_TILE_CHANGE, sig.map_id, sig.y, sig.x, sig.tile_id)
```

---

## Files

- `ninjamagic/bus.py` (add signals)
- `ninjamagic/world/state.py` (add `set_tile`)
- `ninjamagic/mutation.py` (new - processor)
- `ninjamagic/outbox.py` (network encoding)

---

## Acceptance Criteria

- [ ] `MutateTile` signal changes tile
- [ ] `set_tile()` modifies chunk data
- [ ] `TileChanged` signal emitted for network sync
- [ ] Client receives and applies tile changes
- [ ] Test: mutate tile, verify change persists
