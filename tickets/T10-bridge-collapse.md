# T10: Bridge Collapse

**Effort:** S (2h)
**Phase:** Terrain (Week 3)
**Dependencies:** T01, T04

---

## Summary

Bridges burn. When they burn out, they become chasms. Permanent.

---

## Design

### Terrain Types

- `TILE_BRIDGE` - walkable, flammable, burns to chasm
- `TILE_CHASM` - impassable, doesn't block line of sight (you can see across)

Bridge is in T01's `FLAMMABLE` set and `BURNS_TO` dict.

### Collapse Sequence

1. Fire spreads to bridge (T03)
2. Fire intensity exceeds burn threshold (T04)
3. Bridge mutates to chasm (T02)
4. Entities on bridge take fall damage and are displaced/killed

### Fall Damage

When a bridge becomes a chasm with an entity on it:
- Entity takes significant fall damage
- Entity is moved to nearest safe tile (or dies if none)
- Message: "The bridge collapses beneath you!"

This is handled by T02's mutation validation.

### Tactical Use

Burn the bridge behind you to cut off pursuit. Burn the bridge under enemies to drop them. The bridge is a resource - once burned, that route is gone forever.

---

## Acceptance Criteria

- [ ] Bridges are walkable and flammable
- [ ] Fire causes bridges to collapse into chasms
- [ ] Chasms block movement but not vision
- [ ] Entities on collapsing bridge take fall damage
- [ ] Bridge collapse is permanent
