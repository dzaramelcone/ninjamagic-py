# D10: Loot Tables + Item Generation

**Effort:** M (4h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01, D04

---

## Summary

Risk level determines loot quality. Deeper = better drops.

---

## Design

### Risk to Reward

The core loop: deeper is more dangerous, but drops are better. Risk level converts to item level, which affects stats.

Players push deeper because the rewards are worth it.

### Loot Tables

Different sources have different tables:
- **Floor loot** - scattered items, common stuff
- **Chest loot** - better than floor, concentrated
- **Vault loot** - best in dungeon, reward for finding lever
- **Monster drops** - based on creature type

Each table is a weighted list. Roll against weights, check minimum level requirements.

### Rarity

Items have rarity tiers that multiply base stats:
- Common - baseline
- Uncommon - +15%
- Rare - +30%
- Epic - +50%

Higher risk levels shift the rarity distribution toward better outcomes.

### Integration with armor.py

Item effectiveness uses existing contest() math. A level 10 sword vs level 5 armor follows the same probability curves already in the game.

Don't reinvent the wheel - use what exists.

---

## Acceptance Criteria

- [ ] Risk level → item level conversion
- [ ] Weighted loot table selection
- [ ] Rarity affects stat multiplier
- [ ] Different tables for floor/chest/vault
- [ ] Item stats use contest() math
