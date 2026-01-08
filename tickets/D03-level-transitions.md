# D03: Level Transitions

**Effort:** S (2h)
**Phase:** Dungeons (Week 3)
**Dependencies:** D01, D02

---

## Summary

Stairs connect dungeon levels. Players descend deeper or retreat upward.

---

## Design

### Stairs Entity

A Stairs entity is placed during level generation. It knows:
- Direction (up or down)
- Target level and position (where you appear)

Down stairs on level N link to up stairs on level N+1. They're paired - descending and ascending should land you near where you left.

### Stair Layout

- Level 0: down stairs only (entry level)
- Level 1: up and down stairs
- Level 2: up stairs only (bottom floor)

Level 0's up stairs would exit to overworld - that's handled by D02's entrance system.

### Commands

- `descend` - use down stairs when standing on them
- `ascend` - use up stairs when standing on them

If target level hasn't been generated yet, generate it on transition.

### Gameplay

Descending is committing deeper. Ascending is retreating. The tension: better loot below, but harder to escape if things go wrong.

---

## Acceptance Criteria

- [ ] Down stairs placed on levels 0, 1
- [ ] Up stairs placed on levels 1, 2
- [ ] Stairs are paired (down on N links to up on N+1)
- [ ] `descend` and `ascend` commands work
- [ ] Target level generated on first visit
