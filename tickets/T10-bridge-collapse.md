# T10: Bridge Collapse

**Effort:** S (2h)
**Phase:** Terrain (Week 3)
**Dependencies:** T01, T04

---

## Summary

Bridges burn and collapse into chasms when ignited.

---

## Scope

- [ ] Bridge terrain type (walkable, flammable)
- [ ] Chasm terrain type (impassable, transparent)
- [ ] Bridge burns_to chasm
- [ ] Entities on collapsing bridge take fall damage

---

## Technical Details

### Terrain Setup (T01)

```python
TILE_BRIDGE = 25
TILE_CHASM = 26

WALKABLE |= {TILE_BRIDGE}
FLAMMABLE |= {TILE_BRIDGE}
BURNS_TO[TILE_BRIDGE] = TILE_CHASM
```

### Fall Damage

```python
# mutation.py - extend tile change handler
def on_tile_changed(sig: TileChanged):
    if sig.tile_id == TILE_CHASM:
        # Check for entities at this position
        for eid, transform in esper.get_component(Transform):
            if transform.map_id == sig.map_id and transform.y == sig.y and transform.x == sig.x:
                # Entity falls!
                bus.pulse(bus.HealthChanged(source=eid, health_change=-30, damage_type="fall"))
                story.echo("{0} {0:fall} into the chasm!", eid)
                # Move to nearest safe tile or kill
```

---

## Acceptance Criteria

- [ ] Bridges are walkable
- [ ] Fire spreads to bridges
- [ ] Burning bridges become chasms
- [ ] Entities on bridge when it collapses take damage
- [ ] Chasms block movement but not LOS
