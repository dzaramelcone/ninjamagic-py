# D02: Dungeon Entrance Discovery

**Effort:** S (2h)
**Phase:** Dungeons (Week 3)
**Dependencies:** D01

---

## Summary

Players discover dungeon entrances via prompts when entering rooms.

---

## Scope

- [ ] `DungeonEntrance` component
- [ ] Detection when player enters room
- [ ] Prompt: "You notice a passage leading down..."
- [ ] `enter` command to descend

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class DungeonEntrance:
    dungeon_eid: EntityId
    target_level: int = 0
```

### Detection

```python
# entrance.py
def process():
    for sig in bus.iter(bus.MovePosition):
        if not sig.success:
            continue

        # Check for entrance at new position
        for ent_eid, (transform, entrance) in esper.get_components(Transform, DungeonEntrance):
            if transform.map_id != sig.to_map_id:
                continue
            # Check if player is in same room (within 5 tiles)
            if abs(transform.y - sig.to_y) <= 5 and abs(transform.x - sig.to_x) <= 5:
                story.echo("You notice a dark passage leading down...", target=sig.source)
```

### Enter Command

```python
class Enter(Command):
    text: str = "enter"

    def trigger(self, root: bus.Inbound) -> Out:
        # Find nearby entrance
        entrance = find_nearby_entrance(root.source)
        if not entrance:
            return False, "Enter what?"

        bus.pulse(bus.EnterDungeon(source=root.source, entrance=entrance))
        return OK
```

---

## Acceptance Criteria

- [ ] Entrance entities placed in overworld
- [ ] Player sees prompt when near entrance
- [ ] `enter` command transitions to dungeon level 0
- [ ] Dungeon level generated on first entry
