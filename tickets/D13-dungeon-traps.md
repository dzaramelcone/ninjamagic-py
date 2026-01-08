# D13: Dungeon Traps

**Effort:** M (4h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01

---

## Summary

Hidden traps. Step on them, bad things happen. Wit stat lets you spot them first.

---

## Design

### Why Traps?

Traps punish rushing. They reward careful players who watch where they step. Wit stat finally matters in the dungeon.

### Hidden vs Revealed

Traps start hidden. When you step on one, it triggers. But if your Wit is high enough, you spot it first - it becomes revealed on the map, avoidable.

Detection check happens when you get close. High Wit = you see it before you step on it.

### Trap Types

- **Spike trap** - damage
- **Alarm trap** - alerts nearby monsters (now they know you're here)
- **Gas trap** - spawns gas cloud (combine with fire for explosion)
- **Pit trap** - damage + stuck for a turn

Different traps create different situations. Alarm trap in a cleared area is harmless. Alarm trap near a den is deadly.

### Stat Integration

Wit affects detection chance. High Wit players are trap-finders - they scout ahead, reveal dangers for the party.

This gives Wit a clear dungeon role beyond crafting/perception flavor.

---

## Acceptance Criteria

- [ ] Traps hidden until revealed or triggered
- [ ] Movement onto trap triggers effect
- [ ] Wit stat affects detection chance
- [ ] Multiple trap types (spike, alarm, gas, pit)
- [ ] Revealed traps visible on map
