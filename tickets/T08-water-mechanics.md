# T08: Water Mechanics

**Effort:** S (2h)
**Phase:** Terrain (Week 3)
**Dependencies:** T01

---

## Summary

Water slows movement, blocks fire, drowns the unwary.

---

## Design

### Movement Penalty

Water slows you down. Shallow water: 50% slower. Deep water: 100% slower (half speed).

This matters tactically. Chasing someone through water? They have time to prepare. Fighting in water? Everything takes longer.

### Fire Interaction

Water blocks fire spread. Fire cannot spread onto water tiles. Existing fire on water tiles (from explosion overlap?) extinguishes immediately.

Water is the counter to fire. Know where the water is.

### Drowning

Deep water is dangerous for non-swimmers. Entities in deep water without swimming skill take damage over time. The survive system checks this each tick.

Swimming could be a learnable skill, or granted by items (enchanted boots, underwater breathing).

### Depth Matters

Use `water_depth()` from T01:
- Depth 0: not water
- Depth 1: shallow (slow, extinguish, safe)
- Depth 2: deep (very slow, extinguish, drowning)

---

## Acceptance Criteria

- [ ] Shallow water slows movement
- [ ] Deep water slows movement more
- [ ] Fire cannot spread to water tiles
- [ ] Deep water damages non-swimmers
- [ ] `water_depth()` function in T01
