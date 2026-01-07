# D13: Dungeon Traps

**Effort:** M (4h)
**Phase:** Dungeons (Week 5)
**Dependencies:** D01

---

## Summary

Hidden traps triggered by movement. Damage, status effects, or alerts. Wit stat reveals traps.

---

## Scope

- [ ] `Trap` component with trigger and effect
- [ ] Hidden vs revealed trap states
- [ ] Trigger on entity movement
- [ ] Multiple trap types (spike, alarm, gas)
- [ ] Wit-based detection

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class Trap:
    trap_type: str  # spike, alarm, gas, pit
    damage: float = 10.0
    triggered: bool = False
    revealed: bool = False
    detection_dc: int = 15
```

### Trap Types

```python
TRAP_EFFECTS = {
    "spike": {"damage": 15.0, "status": None},
    "alarm": {"damage": 0.0, "status": "alert_mobs"},
    "gas": {"damage": 5.0, "status": "spawn_gas"},
    "pit": {"damage": 20.0, "status": "stuck"},
}
```

### Trigger on Movement

```python
def process():
    for sig in bus.iter(bus.MovePosition):
        if not sig.success:
            continue

        for trap_eid, (transform, trap) in esper.get_components(Transform, Trap):
            if trap.triggered:
                continue
            if transform.y == sig.to_y and transform.x == sig.to_x:
                trigger_trap(trap_eid, sig.source, trap)
```

### Wit Detection

```python
def check_trap_detection(entity_eid, trap_eid, trap):
    stats = esper.try_component(entity_eid, Stats)
    if not stats:
        return False

    wit_bonus = stats.wit * 5
    roll = RNG.randint(1, 20) + wit_bonus

    if roll >= trap.detection_dc:
        trap.revealed = True
        story.echo("{0} {0:spot} a hidden trap!", entity_eid)
        return True
    return False
```

---

## Acceptance Criteria

- [ ] Traps hidden until revealed or triggered
- [ ] Movement onto trap triggers effect
- [ ] Wit stat affects detection chance
- [ ] Multiple trap types with different effects
