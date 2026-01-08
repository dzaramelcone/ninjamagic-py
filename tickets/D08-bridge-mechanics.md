# D08: Bridge Mechanics

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** T01, T04

---

## Summary

Rope bridges over chasms. Burnable. Permanent map changes when destroyed.

---

## Design

### The Fantasy

You're being chased. Behind you, a rope bridge over a bottomless chasm. You cross, torch in hand. Touch it to the ropes. The bridge burns, collapses. Your pursuers stranded on the far side.

Bridges create one-way decisions and dramatic moments.

### Terrain

- `TILE_BRIDGE` - walkable, flammable, burns to chasm
- `TILE_CHASM` - impassable, doesn't block LOS (you can see across)

Fire spreads to bridges (T04). When burned, bridge tiles mutate to chasm tiles. Permanent.

### Tactical Implications

- Cut off pursuit by burning the bridge behind you
- Trap enemies on the far side
- Strand yourself if you're not careful
- Permanent map alteration - that route is gone

### Placement

Bridges span chasms in corridors. Primarily on deeper levels (2+) where the stakes are higher.

A bridge corridor: chasm on both sides, narrow bridge in the middle. Natural chokepoint.

---

## Acceptance Criteria

- [ ] Bridge tiles walkable and flammable
- [ ] Chasm tiles block movement, not vision
- [ ] Fire on bridge causes collapse to chasm
- [ ] Bridges placed in dungeon corridors (level 2+)
- [ ] Entities on bridge when it collapses take fall damage (T02)
