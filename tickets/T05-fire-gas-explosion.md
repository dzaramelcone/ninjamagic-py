# T05: Fire-Gas Explosion

**Effort:** S (2h)
**Phase:** Terrain (Week 2)
**Dependencies:** T03

---

## Summary

Fire ignites gas clouds, causing explosions. Swamp gas becomes deadly.

---

## Scope

- [ ] Detect fire/gas overlap
- [ ] Trigger explosion on contact
- [ ] Explosion consumes gas
- [ ] Explosion spawns more fire
- [ ] Area damage to entities

---

## Technical Details

```python
# fire.py or gas.py
def check_gas_ignition(fire_map_id: int, fire_cells: dict):
    for gas_eid, (transform, gas) in esper.get_components(Transform, Gas):
        if transform.map_id != fire_map_id:
            continue

        for (gy, gx), concentration in gas.dict.items():
            if concentration < 0.1:
                continue
            if (gy, gx) in fire_cells:
                trigger_gas_explosion(gas_eid, gy, gx, concentration)

def trigger_gas_explosion(gas_eid, y, x, concentration):
    # Explosion radius scales with gas concentration
    radius = int(2 + concentration * 3)
    damage = 10 + concentration * 20

    # Damage entities
    for eid, (t, health) in esper.get_components(Transform, Health):
        dist = abs(t.y - y) + abs(t.x - x)
        if dist <= radius:
            bus.pulse(bus.HealthChanged(source=eid, health_change=-damage * (1 - dist/radius)))

    # Spawn fire in radius
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if abs(dy) + abs(dx) <= radius:
                bus.pulse(bus.CreateFire(map_id=transform.map_id, y=y+dy, x=x+dx, seed=RNG.randint(0, 2**31)))

    # Consume gas at explosion point
    gas.dict[(y, x)] = 0
```

---

## Acceptance Criteria

- [ ] Fire touching gas triggers explosion
- [ ] Explosion damages nearby entities
- [ ] Explosion spawns fire in area
- [ ] Gas consumed by explosion
- [ ] Chain reactions possible (fire → more gas)
