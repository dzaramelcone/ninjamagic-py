# T04: Fire Terrain Mutation

**Effort:** S (2h)
**Phase:** Terrain (Week 2)
**Dependencies:** T02, T03

---

## Summary

Fire burns flammable tiles, mutating terrain. Grass becomes ash, bridges collapse.

---

## Scope

- [ ] Fire intensity threshold triggers burn
- [ ] Use `burns_to()` from T01 to determine result
- [ ] Emit `MutateTile` signal when tile burns
- [ ] Track burned tiles to prevent re-burning

---

## Technical Details

```python
# fire.py - add to process loop
BURN_THRESHOLD = 0.5

def check_burns(map_id: int, fire: dict):
    for (y, x), intensity in fire.items():
        if intensity < BURN_THRESHOLD:
            continue

        tile_id = get_tile_id(map_id, y, x)
        new_tile = burns_to(tile_id)

        if new_tile is not None:
            bus.pulse(bus.MutateTile(
                map_id=map_id,
                y=y,
                x=x,
                new_tile=new_tile,
            ))
```

---

## Acceptance Criteria

- [ ] Fire at sufficient intensity burns tiles
- [ ] Grass → burned ground
- [ ] Bridge → chasm (permanent hole)
- [ ] Tile changes sync to clients
