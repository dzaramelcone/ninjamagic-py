# D02: Dungeon Entrance Discovery

**Effort:** S (2h)
**Phase:** Dungeons (Week 3)
**Dependencies:** D01

---

## Summary

How players find and enter dungeons from the overworld.

---

## Design

### Entrance Entity

A DungeonEntrance is an entity placed on the overworld map. It links to a specific dungeon and target level (usually 0).

Entrances are visible terrain features - a cave mouth, crumbling stairs, a pit. Players see them on the map.

### Discovery Prompt

When a player moves near an entrance they haven't entered before, they get a prompt:

> "You notice a dark passage leading down..."

This is flavor, not a gate. The entrance is always usable.

### Enter Command

`enter` command when near an entrance transitions the player to dungeon level 0. This triggers lazy generation if the level hasn't been built yet.

### Open Questions

- Should some entrances be hidden until discovered (perception check, exploration)?
- Can entrances be blocked/locked (key required, boss guards it)?
- Do entrances close/collapse (time pressure, one-way trips)?

For Q1: keep it simple. Entrances are visible and always open.

---

## Acceptance Criteria

- [ ] Entrance entities can be placed on overworld
- [ ] Player sees discovery prompt when first approaching
- [ ] `enter` command moves player to dungeon level 0
- [ ] First entry triggers level generation
