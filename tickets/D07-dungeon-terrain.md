# D07: Dungeon Terrain Integration

**Effort:** M (4h)
**Phase:** Dungeons (Week 4)
**Dependencies:** T01, D01

---

## Summary

Dungeons use the terrain system. Each level has environmental variety - water, swamp, magma.

---

## Design

### Terrain as Content

Terrain isn't just walls and floors. It's gameplay. A water pool room plays differently than a magma room. The terrain system (T01-T10) provides the mechanics; this ticket places them.

### Room Variants

Not every room is the same. During generation, some rooms become:

- **Water pool room** - central pool of shallow/deep water. Slows movement, extinguishes fire, drowns the unwary.
- **Swamp pocket** - emits gas (T09). Waiting to be ignited.
- **Magma room** - level 2 only. Deadly to cross, lights up the space.
- **Standard room** - stone floor, no hazards.

Percentages tuned by feel. Maybe 15% water, 10% swamp, 5% magma (deep only).

### Dungeon ChipSet

Dungeons need their own tileset - stone instead of dirt, dungeon-specific water colors. The ChipSet maps tile IDs to glyphs and colors.

### Theme Variation

Different dungeon themes (cave, ruin, hell) might weight room variants differently. Hell dungeon = more magma. Ruin = more chasms.

For Q1: one theme (cave), basic variant distribution.

---

## Acceptance Criteria

- [ ] Dungeon levels use dungeon-specific ChipSet
- [ ] Water pool rooms generated
- [ ] Swamp pocket rooms emit gas
- [ ] Magma rooms on level 2+ deal damage
- [ ] Terrain mechanics (fire, water, gas) work in dungeons
