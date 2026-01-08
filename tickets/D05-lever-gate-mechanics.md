# D05: Lever-Gate Mechanics

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** D04

---

## Summary

Levers open vault gates. Action at a distance - pull here, something opens over there.

---

## Design

### The Interaction

Lever is an entity you can interact with. Stand next to it, `pull lever`. It triggers its linked gate to open.

"A grinding noise echoes from somewhere deeper in the dungeon..."

The player has to remember where the vault was, or discover it after pulling. Information asymmetry creates exploration.

### Lever Properties

- One-use: once pulled, stays pulled
- Linked: knows which vault gate it controls
- Visible: has a glyph on the map, interactable noun ("rusty lever")

### Placement

Lever is placed in a different room from its vault. Finding the lever is part of the challenge. The lever might be:
- Behind enemies
- Past a trap
- In an optional side room

### Future Extensions

Levers could do more than open vaults:
- Close gates (trap players/monsters)
- Trigger traps
- Release caged creatures
- Toggle bridges

For Q1: lever opens vault gate. Keep it simple.

---

## Acceptance Criteria

- [ ] Lever entity with visible glyph
- [ ] `pull lever` command when adjacent
- [ ] Pulling triggers linked vault gate to open
- [ ] Lever can only be pulled once
- [ ] Feedback message on pull
