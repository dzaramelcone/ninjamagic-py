# D01: Dungeon Entity Pipeline

**Effort:** M (4h)
**Phase:** Dungeons (Week 3)
**Dependencies:** None

---

## Summary

Dungeons are multi-level maps that players descend into. This ticket creates the entity structure and entry point for dungeon creation.

---

## Design

### Entity Structure

A **Dungeon** is a parent entity that owns multiple **DungeonLevel** entities. Each level is a separate map (has its own Chips/ChipSet).

- Dungeon holds metadata: name, theme (cave/ruin/hell), base difficulty
- Each level is a map entity linked back to its parent dungeon
- Levels are generated lazily - map data created when first player enters

### Depth and Risk

Deeper levels are harder. Risk level drives mob spawns, loot quality, trap density.

Simple linear scaling: `risk = base_risk + (depth * 15)`

A base_risk 10 dungeon:
- Level 0: risk 10 (entry, tutorial difficulty)
- Level 1: risk 25 (main challenge)
- Level 2: risk 40 (boss floor, high reward)

### Themes

Theme affects tileset, mob types, and flavor. Start with one (cave), expand later.

---

## Acceptance Criteria

- [ ] Dungeon entity created with name and theme
- [ ] 3 level entities linked to parent dungeon
- [ ] Risk increases with depth
- [ ] Levels don't generate map data until entered
- [ ] Entry point function to create a dungeon
