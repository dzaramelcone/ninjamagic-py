# D06: Monster Den Placement

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** D01

---

## Summary

Monster dens are spawn points. Creatures emerge when players get close.

---

## Design

### Why Dens?

Dens pace the dungeon. You don't get swarmed at the entrance. Monsters appear as you explore, creating tension and ambush moments.

A den is a visible feature - a nest, a burrow, bones piled in a corner. Players learn to recognize danger before they trigger it.

### Spawn Trigger

Dens are dormant until a player gets within range (~8 tiles). Then they spawn their creatures and mark themselves as triggered.

One-time spawn. Den doesn't respawn on its own (world regen during nightstorm might reset them - that's a separate system).

### Creature Scaling

Creature type matches risk level:
- Low risk (level 0): rats, bats, spiders - nuisances
- Medium risk (level 1): goblins, wolves - real threats
- High risk (level 2): trolls, wraiths - deadly

### Den Density

More dens on deeper levels. Level 0 might have 1 den. Level 2 might have 3-4.

Formula: `num_dens = 1 + (risk_level // 15)`

### Multiplayer Dynamics

First player to trigger a den wakes the monsters. Other players might hear combat and come help - or stay back and let them soften each other up.

---

## Acceptance Criteria

- [ ] Den entities placed in side rooms
- [ ] Dens spawn creatures on player proximity
- [ ] Creature types scale with risk level
- [ ] Den count scales with risk level
- [ ] Dens only trigger once
