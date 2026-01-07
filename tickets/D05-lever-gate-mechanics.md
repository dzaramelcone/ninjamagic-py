# D05: Lever-Gate Mechanics

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** D04

---

## Summary

Levers open vault gates. Pull lever in one room, gate opens elsewhere.

---

## Scope

- [ ] `Lever` component with target vault
- [ ] Lever entity with visual glyph
- [ ] `pull <lever>` command
- [ ] Lever placement in non-vault room
- [ ] Gate opening animation/feedback

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class Lever:
    target_vault: EntityId
    pulled: bool = False
```

### Lever Entity

```python
def create_lever(level_eid: EntityId, y: int, x: int, vault_eid: EntityId):
    lever = esper.create_entity(
        Transform(map_id=level_eid, y=y, x=x),
        Lever(target_vault=vault_eid),
        Noun(value="lever", adjective="rusty"),
    )
    esper.add_component(lever, ("╥", 0.08, 0.4, 0.5), Glyph)
    return lever
```

### Pull Command

```python
class Pull(Command):
    text: str = "pull"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Pull what?"

        match = find_adjacent(root.source, rest, with_components=(Lever,))
        if not match:
            return False, "Pull what?"

        lever_eid, _, _ = match
        bus.pulse(bus.PullLever(source=root.source, lever=lever_eid))
        return OK
```

### Lever Handler

```python
def process():
    for sig in bus.iter(bus.PullLever):
        lever = esper.component_for_entity(sig.lever, Lever)
        if lever.pulled:
            story.echo("The lever has already been pulled.", target=sig.source)
            continue

        lever.pulled = True
        open_vault(lever.target_vault)

        story.echo("{0} {0:pull} the lever. A grinding noise echoes...", sig.source)
```

---

## Acceptance Criteria

- [ ] Lever entities placed in dungeon
- [ ] `pull lever` command works
- [ ] Pulling lever opens linked vault gate
- [ ] Lever can only be pulled once
- [ ] Sound/message feedback
