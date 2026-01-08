# D11: Treasure Chests

**Effort:** S (2h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01, D10

---

## Summary

Chests are containers. Open them to get loot.

---

## Design

### The Chest

A chest is an entity with:
- Position in the dungeon
- Risk level (determines loot quality)
- Open/closed state
- Visual glyph that changes when opened

Chests are one-time. Once opened, they stay open.

### Interaction

Stand next to chest, `open chest`. Items drop on the ground (or into inventory, depending on system).

"You open the chest and find a rusty dagger and some gold coins."

### Placement

Chests scattered in side rooms. Not every room has one. Finding a chest is a small reward for exploration.

Vaults have special chest placement (D04) with better loot tables.

### Multiplayer

First player to open gets the loot. Creates soft competition - do you split up to find more chests, or stick together for safety?

---

## Acceptance Criteria

- [ ] Chest entity with risk level
- [ ] `open chest` command when adjacent
- [ ] Loot generated from table on open
- [ ] Chest glyph changes when opened
- [ ] Chests placed during generation
