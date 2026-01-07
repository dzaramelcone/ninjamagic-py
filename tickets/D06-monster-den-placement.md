# D06: Monster Den Placement

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** D01

---

## Summary

Monster dens spawn creatures. More dens on deeper levels.

---

## Scope

- [ ] `MonsterDen` component
- [ ] Den placement during generation
- [ ] Creature spawning from dens
- [ ] Den creature types per depth

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class MonsterDen:
    creature_type: str
    spawn_count: int = 3
    spawned: bool = False
```

### Placement

```python
def place_monster_dens(level_eid: EntityId, rooms: dict, risk_level: int):
    num_dens = 1 + risk_level // 15

    side_rooms = [pos for pos, room in rooms.items() if isinstance(room, SideRoom)]
    den_rooms = RNG.sample(side_rooms, min(num_dens, len(side_rooms)))

    for room_pos in den_rooms:
        top = room_pos[0] * TILE_STRIDE_H
        left = room_pos[1] * TILE_STRIDE_W

        creature_type = get_creature_for_risk(risk_level)
        create_monster_den(level_eid, top + 8, left + 8, creature_type, risk_level)
```

### Creature Types by Risk

```python
def get_creature_for_risk(risk_level: int) -> str:
    if risk_level < 15:
        return RNG.choice(["rat", "bat", "spider"])
    elif risk_level < 30:
        return RNG.choice(["goblin", "wolf", "crawler"])
    else:
        return RNG.choice(["troll", "wraith", "ogre"])
```

### Den Spawning

```python
def process_dens():
    for eid, (transform, den) in esper.get_components(Transform, MonsterDen):
        if den.spawned:
            continue

        # Check for player proximity to trigger
        for player_eid, (pt,) in esper.get_components(Transform):
            if pt.map_id != transform.map_id:
                continue
            if abs(pt.y - transform.y) <= 8 and abs(pt.x - transform.x) <= 8:
                spawn_from_den(eid, transform, den)
                break
```

---

## Acceptance Criteria

- [ ] MonsterDen entities placed in rooms
- [ ] Dens spawn creatures when player approaches
- [ ] Creature types scale with risk level
- [ ] 1-3 dens per level based on risk
