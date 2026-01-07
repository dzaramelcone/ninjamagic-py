# D09: Procedural Dungeon Fauna

**Effort:** M (4h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01, D06

---

## Summary

Generate thematic creature populations for dungeon levels. Fauna varies by depth, terrain, and room type.

---

## Scope

- [ ] `FaunaTable` per dungeon theme/depth
- [ ] Ambient creature spawning (non-hostile initially)
- [ ] Creature placement in appropriate rooms
- [ ] Fauna density scaling with risk level

---

## Technical Details

### Fauna Tables

```python
@dataclass(frozen=True)
class FaunaEntry:
    creature_type: str
    weight: int
    min_depth: int = 0
    max_depth: int = 99
    terrain_types: frozenset[int] | None = None

CAVE_FAUNA: list[FaunaEntry] = [
    FaunaEntry("rat", weight=10),
    FaunaEntry("bat", weight=8),
    FaunaEntry("spider", weight=5, min_depth=1),
    FaunaEntry("crawler", weight=3, min_depth=2),
    FaunaEntry("cave_fish", weight=6, terrain_types=frozenset({TILE_DUNGEON_WATER_SHALLOW})),
]
```

### Weighted Selection

```python
def select_creature(table: list[FaunaEntry], depth: int, terrain: int | None = None) -> str | None:
    valid = [
        e for e in table
        if e.min_depth <= depth <= e.max_depth
        and (e.terrain_types is None or terrain in e.terrain_types)
    ]
    if not valid:
        return None

    total = sum(e.weight for e in valid)
    roll = RNG.random() * total
    cumulative = 0
    for entry in valid:
        cumulative += entry.weight
        if roll < cumulative:
            return entry.creature_type
    return valid[-1].creature_type
```

---

## Acceptance Criteria

- [ ] Fauna tables define creatures per theme
- [ ] Creatures spawn in appropriate rooms
- [ ] Terrain-specific creatures near matching tiles
- [ ] Fauna density scales with risk level
