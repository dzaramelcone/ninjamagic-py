# D10: Loot Tables + Item Generation

**Effort:** M (4h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01, D04

---

## Summary

Risk level → item level. Loot tables generate items with tiered effectiveness using contest() math from armor.py.

---

## Scope

- [ ] `LootTable` with weighted entries
- [ ] Item generation from templates + risk level
- [ ] Item level scaling using contest() pattern
- [ ] Rarity scalar affects stat rolls

---

## Technical Details

### Rarity System

```python
class Rarity(IntEnum):
    COMMON = 0      # 60% - base stats
    UNCOMMON = 1    # 25% - +15% stats
    RARE = 2        # 12% - +30% stats
    EPIC = 3        # 3%  - +50% stats

RARITY_WEIGHTS = [60, 25, 12, 3]
RARITY_BONUS = [1.0, 1.15, 1.30, 1.50]
```

### Item Level from Risk

```python
def risk_to_item_level(risk_level: int) -> int:
    if risk_level < 20:
        return 1 + risk_level // 4
    elif risk_level < 50:
        return 5 + (risk_level - 20) // 3
    else:
        return 15 + (risk_level - 50) // 4
```

### Loot Tables

```python
DUNGEON_LOOT: list[LootEntry] = [
    LootEntry("dagger", weight=10),
    LootEntry("short_sword", weight=8),
    LootEntry("leather_armor", weight=6),
    LootEntry("potion_health", weight=15),
    LootEntry("gold_coins", weight=20),
]

VAULT_LOOT: list[LootEntry] = [
    LootEntry("long_sword", weight=8, min_level=5),
    LootEntry("plate_armor", weight=3, min_level=10),
    LootEntry("ring_protection", weight=5),
    LootEntry("gold_pile", weight=15),
]
```

---

## Acceptance Criteria

- [ ] Risk level converts to item level
- [ ] Rarity roll affects stat multiplier
- [ ] Items generated with scaled ranks
- [ ] contest() math determines effectiveness
