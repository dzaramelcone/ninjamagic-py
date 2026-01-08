# D09: Procedural Dungeon Fauna

**Effort:** M (4h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01, D06

---

## Summary

Each dungeon level has a creature population. What lives here depends on depth, terrain, and theme.

---

## Design

### Living Dungeons

Dungeons aren't just monster closets. They're ecosystems. Rats scurry in shallow tunnels. Cave fish swim in underground pools. Spiders lurk in deeper, darker places.

Fauna makes dungeons feel inhabited, not spawned.

### Fauna Tables

A fauna table is a weighted list of creature types, filtered by:
- **Depth** - some creatures only appear on deeper levels
- **Terrain** - cave fish need water, fire salamanders need magma
- **Theme** - ruin dungeons have different fauna than caves

### Ambient vs Hostile

Not everything attacks on sight. Some fauna is ambient - rats that flee, bats that scatter. Hostility is a creature property, not a fauna property.

This creates variety. Not every encounter is combat.

### Terrain-Specific Creatures

The interesting design: creatures that only spawn near matching terrain.
- Cave fish in water pools
- Gas beetles near swamp
- Salamanders near magma

This ties fauna to environment, rewards paying attention to terrain.

---

## Acceptance Criteria

- [ ] Fauna tables per dungeon theme
- [ ] Creature selection weighted by type
- [ ] Depth filtering for tougher creatures
- [ ] Terrain-specific creatures near matching tiles
- [ ] Ambient and hostile creatures mixed
