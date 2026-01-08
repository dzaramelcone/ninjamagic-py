# T06: Fire Entity Damage

**Effort:** S (2h)
**Phase:** Terrain (Week 2)
**Dependencies:** T03

---

## Summary

Entities in fire take damage over time. Standing in flames hurts.

---

## Scope

- [ ] Check entity positions against fire cells
- [ ] Apply damage based on fire intensity
- [ ] Armor modifies fire damage (plate amplifies, cloth resists)
- [ ] Visual feedback for burning status

---

## Technical Details

```python
# fire.py
def apply_fire_damage():
    for fire_eid, (transform, fire_state) in esper.get_components(Transform, FireState):
        fire_cells = compute_fire_state(
            transform.map_id,
            fire_state.origin_y, fire_state.origin_x,
            fire_state.seed, fire_state.start_tick,
        )

        for eid, (t, health) in esper.get_components(Transform, Health):
            if t.map_id != transform.map_id:
                continue

            intensity = fire_cells.get((t.y, t.x), 0)
            if intensity > 0.1:
                damage = intensity * FIRE_DAMAGE_MULT
                # Armor modifies fire damage
                if armor := esper.try_component(eid, Armor):
                    damage *= armor.fire_mult  # plate=1.5, leather=1.0, cloth=0.5
                bus.pulse(bus.HealthChanged(
                    source=eid,
                    health_change=-damage,
                    damage_type="fire",
                ))
```

---

## Acceptance Criteria

- [ ] Entities in fire tiles take damage
- [ ] Damage scales with fire intensity
- [ ] Armor type modifies fire damage (plate amplifies, magical cloth resists)
- [ ] Players see "You are burning!" message
