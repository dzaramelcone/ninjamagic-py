# D03: Level Transitions

**Effort:** S (2h)
**Phase:** Dungeons (Week 3)
**Dependencies:** D01, D02

---

## Summary

Stairs connect dungeon levels. Descend/ascend between floors.

---

## Scope

- [ ] `Stairs` component (up/down, target level)
- [ ] Stair placement during generation
- [ ] `descend` and `ascend` commands
- [ ] Level generation on first visit

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class Stairs:
    direction: str  # "up" or "down"
    target_level_eid: EntityId
    target_y: int
    target_x: int
```

### Placement

```python
def place_stairs(level_eid: EntityId, depth: int, dungeon_eid: EntityId):
    # Down stairs (except on level 2)
    if depth < 2:
        next_level = get_level(dungeon_eid, depth + 1)
        create_stairs(level_eid, "down", next_level, room_pos)

    # Up stairs (except on level 0)
    if depth > 0:
        prev_level = get_level(dungeon_eid, depth - 1)
        create_stairs(level_eid, "up", prev_level, room_pos)
```

### Commands

```python
class Descend(Command):
    text: str = "descend"

    def trigger(self, root: bus.Inbound) -> Out:
        stairs = find_stairs_at(root.source, "down")
        if not stairs:
            return False, "There are no stairs leading down here."

        bus.pulse(bus.UseStairs(source=root.source, stairs_eid=stairs))
        return OK
```

---

## Acceptance Criteria

- [ ] Down stairs on levels 0, 1
- [ ] Up stairs on levels 1, 2
- [ ] `descend` moves to next level
- [ ] `ascend` moves to previous level
- [ ] Levels generated lazily on first visit
