# T09: Swamp Gas Emission

**Effort:** S (2h)
**Phase:** Terrain (Week 3)
**Dependencies:** T01

---

## Summary

Swamp tiles emit gas. Gas builds up. Fire makes it explode.

---

## Design

### Passive Danger

Swamp doesn't attack you directly. It emits gas over time. The gas spreads, accumulates, waits.

Bring fire into a swamp area? Boom.

### Emission Rate

Swamp tiles emit small amounts of gas periodically. Gas spreads via existing diffusion (gas.py). Over time, swamp areas become saturated with flammable gas.

Tuning: emit rate, emit amount, gas decay. Too fast = always dangerous. Too slow = never relevant. Find the tension.

### Integration

- Uses `emits_gas()` from T01 to identify swamp tiles
- Uses existing gas.py for diffusion
- Ties into T05 for fire-gas explosion

### Gameplay

Swamp areas are trap zones. Safe to walk through... until someone lights a torch. Then they're death traps.

Players learn: don't bring fire into swamp. Or do, if your enemies are there.

---

## Acceptance Criteria

- [ ] Swamp tiles emit gas periodically
- [ ] Gas accumulates in swamp areas
- [ ] Gas spreads using existing diffusion system
- [ ] Fire ignites accumulated gas (T05)
