# D14: Prefab Expansion

**Effort:** M (4h)
**Phase:** Dungeons (Week 3-4)
**Dependencies:** D01, D04, D07

---

## Summary

Room templates for dungeon generation. ASCII art → playable content.

---

## Design

### Simple Rules, Complex Results

Prefabs are ASCII layouts with a legend. Each character maps to a tile type or feature marker.

```
################
#..............#
#....~~~.......#
#...~~≈~~......#
#....~~~.......#
#..............#
################
```

This is a water pool room. The generator stamps it, translates characters, places features. Done.

### Prefab Structure

A prefab is:
- **Layout** - ASCII grid
- **Legend** - character → tile ID mapping
- **Features** - marker → entity type (C = chest, L = lever, D = den)
- **Min risk** - only appears at or above this risk level

### Room Types

Different prefabs for different purposes:
- **Standard rooms** - floor and walls
- **Water pool rooms** - central water feature
- **Swamp rooms** - gas-emitting terrain
- **Magma rooms** - dangerous crossing
- **Vault rooms** - gate + treasure area
- **Bridge corridors** - chasm with narrow crossing

### Feature Markers

Special characters that spawn entities, not terrain:
- `C` → chest
- `L` → lever
- `D` → monster den
- `B` → explosive barrel
- `T` → trap

Generator sees marker, spawns entity, places floor underneath.

### Why Prefabs?

Hand-authored rooms feel designed. Procedural assembly feels infinite. Prefabs give you both - human-designed moments, procedurally arranged.

Conway showed us: simple rules, complex results.

---

## Acceptance Criteria

- [ ] Prefab data structure (layout, legend, features)
- [ ] Standard room prefabs
- [ ] Terrain variant prefabs (water, swamp, magma)
- [ ] Vault room prefab
- [ ] Bridge corridor prefab
- [ ] Feature markers spawn correct entities
