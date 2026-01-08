# T03: Fire Spread Core

**Effort:** M (4h)
**Phase:** Terrain (Week 1)
**Dependencies:** T01

---

## Summary

Fire spreads across flammable terrain. The core Brogue mechanic.

---

## Q1 Scope

**Keep it simple.** Server-authoritative, sync state directly. Accept visual jank.

The gameplay decision ("lure enemy into grass, light it") works even without buttery smooth client simulation. Rich simulation interactions (water flooding, steam, mud golems) are post-launch.

---

## Design

### Fire as Data

Fire is intensity values on a grid. Each tick:
1. Spread to adjacent flammable tiles
2. Decay intensity
3. Burn tiles that hit threshold
4. Die when all intensity gone

### Network Strategy

Two options considered:

**Option A: Seed-based determinism**
Send origin + seed, client reconstructs spread locally. 160x bandwidth reduction. But terrain mutations cause divergence - fire burns grass, client might be out of sync.

**Option B: Server-authoritative state sync**
Server is truth. Send fire state directly. More bandwidth, simpler to reason about, no divergence bugs.

**For Q1: Option B.** Get it working, optimize later if bandwidth is actually a problem.

### Signals

- `CreateFire` - fire starts at position
- `FireExtinguished` - fire is gone (client cleanup)
- Fire state syncs via regular outbox updates

---

## Open Design Questions

**Simulation interactions:**
Fire + gas = explosion. Fire + water = extinguish. Two simulations need consistent state.

Options:
- Sync explosions as discrete events (not continuous simulation)
- Server runs all simulations, clients just render state
- Accept minor visual divergence, enforce gameplay consistency

**Potential refactor: global fire layer**
If multiple fires get complex, consider single intensity layer per map (like gas). Explosions add intensity rather than spawning entities. Cleaner model.

Needs design spike before implementation.

---

## Acceptance Criteria

- [ ] Fire spreads to adjacent flammable tiles
- [ ] Fire intensity decays over time
- [ ] Fire extinguishes when intensity hits zero
- [ ] Fire state syncs to clients
- [ ] Fire extinguished events sync to clients
