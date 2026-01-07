# T08: Water Mechanics

**Effort:** S (2h)
**Phase:** Terrain (Week 3)
**Dependencies:** T01

---

## Summary

Water tiles slow movement and extinguish fire.

---

## Scope

- [ ] Water depth affects movement speed
- [ ] Deep water requires swimming (or drowning)
- [ ] Water extinguishes fire on contact
- [ ] Wading visual/sound effects

---

## Technical Details

### Movement Cost

```python
# Already in T01
MOVEMENT_COST[TILE_WATER_SHALLOW] = 1.5
MOVEMENT_COST[TILE_DUNGEON_WATER_DEEP] = 2.0
```

### Fire Extinguishing

```python
# fire.py
def _can_spread(map_id: int, y: int, x: int) -> bool:
    tile_id = get_tile_id(map_id, y, x)
    if is_water(tile_id):
        return False  # water blocks fire spread
    return is_flammable(tile_id)
```

### Deep Water Drowning

```python
# survive.py - add to process
def check_drowning():
    for eid, (transform, health) in esper.get_components(Transform, Health):
        tile = get_tile_id(transform.map_id, transform.y, transform.x)
        if water_depth(tile) >= 2:
            # Check for swimming skill or apply damage
            if not has_skill(eid, "swimming"):
                bus.pulse(bus.HealthChanged(source=eid, health_change=-5, damage_type="drowning"))
```

---

## Acceptance Criteria

- [ ] Shallow water slows movement 50%
- [ ] Deep water slows movement 100%
- [ ] Fire cannot spread to water tiles
- [ ] Fire in water tiles extinguishes
- [ ] Deep water damages non-swimmers
