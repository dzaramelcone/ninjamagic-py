# D04: Vault Generation

**Effort:** M (4h)
**Phase:** Dungeons (Week 4)
**Dependencies:** D01, D05

---

## Summary

Vaults are locked treasure rooms. Gate bars entry until a lever opens it.

---

## Design

### The Vault Fantasy

You see the loot through the bars. Can't reach it. Somewhere on this level is a lever. Find it, pull it, gates open. But maybe someone else is racing for the same lever. Maybe a monster is between you and it.

Vaults create objectives. They pull players through the level.

### Structure

A vault is a room with:
- Gate tiles blocking the entrance (impassable terrain)
- High-value loot inside (visible but unreachable)
- A linked lever somewhere else on the level

### Gate Mechanics

Gates use terrain mutation (T02):
- `TILE_GATE_CLOSED` - blocks movement, doesn't block LOS (you can see through)
- `TILE_GATE_OPEN` - walkable

When lever is pulled (D05), gate tiles mutate from closed to open.

### Placement

- No vault on level 0 (entry level should be simple)
- One vault per level on depths 1 and 2
- Vault loot scales with risk level

### Loot

Vault loot is better than floor loot. Higher tier items, guaranteed drops. The reward for finding the lever and surviving the trip.

---

## Acceptance Criteria

- [ ] Vault room generated with gate blocking entrance
- [ ] Gate blocks movement but not vision
- [ ] Vault contains high-tier loot
- [ ] One vault per level (depth 1+)
- [ ] Gate opens via lever (D05)
