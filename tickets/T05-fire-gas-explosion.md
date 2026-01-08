# T05: Fire-Gas Explosion

**Effort:** S (2h)
**Phase:** Terrain (Week 2)
**Dependencies:** T03

---

## Summary

Fire ignites gas. Gas explodes. Swamp becomes a death trap.

---

## Design

### The Interaction

Fire and gas overlap → explosion. This is the payoff for swamp areas. The gas is harmless until someone brings fire. Then it's catastrophic.

### Explosion Effects

When fire touches gas:
1. **Area damage** - entities in radius take damage, falloff with distance
2. **Fire spread** - explosion spawns fire in the blast radius
3. **Gas consumed** - the gas at that point is gone

### Chain Reactions

Explosion spawns fire. Fire can reach more gas. More explosions. A single torch in a gas-filled room can cascade into total destruction.

This is emergent - we don't code "chain reaction", we code "fire spreads" and "fire ignites gas". The chain emerges.

### Explosion as Event

Explosions sync as discrete events, not continuous simulation. Server detects overlap, emits explosion signal, clients render the boom. No determinism problems.

---

## Acceptance Criteria

- [ ] Fire touching gas triggers explosion
- [ ] Explosion deals AoE damage (falloff with distance)
- [ ] Explosion spawns fire in radius
- [ ] Gas consumed at explosion point
- [ ] Chain reactions emerge naturally
