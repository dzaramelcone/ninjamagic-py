# D01: Dungeon Entity Pipeline

**Effort:** M (4h)
**Phase:** Dungeons (Week 3)
**Dependencies:** None

---

## Summary

Create dungeons as map entities with multi-level structure. Entry point for all dungeon generation.

---

## Current State

- Maps are entities with Chips, ChipSet components
- `simple.py` generates single-level maps
- No dungeon entity structure
- No level transitions

---

## Scope

- [ ] `Dungeon` component with metadata
- [ ] `DungeonLevel` component per level
- [ ] 3 levels per dungeon
- [ ] Risk level calculation (depth-based)
- [ ] Entry point: `create_dungeon()`

---

## Technical Details

### Components

```python
@component(slots=True, kw_only=True)
class Dungeon:
    """Top-level dungeon entity."""
    name: str
    theme: str = "cave"  # cave, ruin, hell
    num_levels: int = 3
    base_risk: int = 10

@component(slots=True, kw_only=True)
class DungeonLevel:
    """Single level within a dungeon."""
    dungeon_eid: EntityId
    depth: int  # 0, 1, 2
    risk_level: int
    generated: bool = False
```

### Creation

```python
def create_dungeon(name: str, theme: str = "cave", base_risk: int = 10) -> EntityId:
    """Create a dungeon with 3 levels."""
    dungeon_eid = esper.create_entity(
        Dungeon(name=name, theme=theme, base_risk=base_risk),
    )

    for depth in range(3):
        risk = base_risk + depth * 15
        level_eid = esper.create_entity(
            DungeonLevel(dungeon_eid=dungeon_eid, depth=depth, risk_level=risk),
            Chips(dict={}),
            ChipSet(list=[]),
        )

    return dungeon_eid
```

### Risk Calculation

```
Level 0: base_risk + 0  (e.g., 10)
Level 1: base_risk + 15 (e.g., 25)
Level 2: base_risk + 30 (e.g., 40)
```

---

## Files

- `ninjamagic/component.py` (Dungeon, DungeonLevel)
- `ninjamagic/dungeon.py` (new - creation pipeline)

---

## Acceptance Criteria

- [ ] Dungeon entity created with name/theme
- [ ] 3 DungeonLevel entities linked to dungeon
- [ ] Risk level increases with depth
- [ ] Levels start ungenerated (lazy generation)
