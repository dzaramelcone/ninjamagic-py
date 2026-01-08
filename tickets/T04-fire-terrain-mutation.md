# T04: Fire Terrain Mutation

**Effort:** S (2h)
**Phase:** Terrain (Week 2)
**Dependencies:** T02, T03

---

## Summary

Fire burns terrain. Grass becomes ash. Bridges become chasms.

---

## Design

### Burn Threshold

Fire doesn't instantly burn things. Intensity must exceed a threshold before terrain mutates. This gives players a moment to react - see the fire spreading, decide to flee or fight it.

### Integration

Fire system checks each burning tile:
1. Is intensity above burn threshold?
2. What does this tile burn to? (`burns_to()` from T01)
3. Emit `MutateTile` signal

The mutation system (T02) handles the actual tile change and consequences (entities on collapsing bridges, etc).

### Terrain Transformations

- Grass → burned ground (safe to walk, no longer flammable)
- Dry grass → burned ground (burns faster than regular grass)
- Bridge → chasm (permanent, deadly)

### One-Way Changes

Burned terrain doesn't heal on its own. Grass doesn't regrow (until world regen during nightstorm, separate system). Bridges don't rebuild.

Fire has permanent consequences. That's the point.

---

## Acceptance Criteria

- [ ] Fire at sufficient intensity triggers burn
- [ ] Grass → burned ground
- [ ] Bridge → chasm
- [ ] Uses `burns_to()` from T01
- [ ] Emits `MutateTile` for terrain change
