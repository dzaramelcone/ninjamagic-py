# D11: Treasure Chests

**Effort:** S (2h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01, D10

---

## Summary

Chests contain loot. Open with `open <chest>` command. Risk level determines contents.

---

## Scope

- [ ] `Chest` component with contents
- [ ] Chest entity with visual glyph
- [ ] `open <chest>` command
- [ ] Chest placement during dungeon generation

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class Chest:
    risk_level: int
    opened: bool = False
    loot_count: int = 3
```

### Open Command

```python
class Open(Command):
    text: str = "open"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        match = find_adjacent(root.source, rest, with_components=(Chest,))
        if not match:
            return False, "Open what?"

        chest_eid, _, _ = match
        bus.pulse(bus.OpenChest(source=root.source, chest=chest_eid))
        return OK
```

### Open Handler

```python
def process():
    for sig in bus.iter(bus.OpenChest):
        chest = esper.component_for_entity(sig.chest, Chest)
        if chest.opened:
            story.echo("{0} {0:find} the chest empty.", sig.source)
            continue

        chest.opened = True
        items = generate_loot(chest.risk_level, DUNGEON_LOOT, chest.loot_count)
        # Drop items at chest location
        story.echo("{0} {0:open} the chest.", sig.source)
```

---

## Acceptance Criteria

- [ ] Chest entities with risk level
- [ ] `open chest` command works
- [ ] Loot generated on open
- [ ] Chest glyph changes when opened
