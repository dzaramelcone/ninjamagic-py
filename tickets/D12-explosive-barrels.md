# D12: Explosive Barrels

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** T03, T05, D01

---

## Summary

Barrels of volatile liquid. Fire → explosion → area damage + fire spread. Environmental weapon.

---

## Scope

- [ ] `ExplosiveBarrel` component
- [ ] Barrel entity with visual glyph
- [ ] Fire contact triggers explosion
- [ ] Explosion damages nearby entities
- [ ] Explosion spawns fire in radius

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class ExplosiveBarrel:
    explosion_radius: int = 3
    explosion_damage: float = 25.0
    triggered: bool = False
```

### Explosion Trigger

```python
def process():
    for eid, (transform, barrel) in esper.get_components(Transform, ExplosiveBarrel):
        if barrel.triggered:
            continue

        if has_fire_at(transform.map_id, transform.y, transform.x):
            trigger_explosion(eid, transform, barrel)

def trigger_explosion(barrel_eid, transform, barrel):
    barrel.triggered = True

    # Damage entities in radius
    for eid, (t, health) in esper.get_components(Transform, Health):
        dist = abs(t.y - transform.y) + abs(t.x - transform.x)
        if dist <= barrel.explosion_radius:
            damage = barrel.explosion_damage * (1.0 - dist / (barrel.explosion_radius + 1))
            bus.pulse(bus.HealthChanged(source=eid, health_change=-damage))

    # Spawn fire in radius
    for dy in range(-barrel.explosion_radius, barrel.explosion_radius + 1):
        for dx in range(-barrel.explosion_radius, barrel.explosion_radius + 1):
            if abs(dy) + abs(dx) <= barrel.explosion_radius:
                bus.pulse(bus.CreateFire(map_id=transform.map_id, y=transform.y+dy, x=transform.x+dx, seed=RNG.randint(0, 2**31)))

    esper.delete_entity(barrel_eid)
```

---

## Acceptance Criteria

- [ ] Barrel entities placed in dungeons
- [ ] Fire contact triggers explosion
- [ ] Explosion damages entities in radius
- [ ] Explosion spawns fires
