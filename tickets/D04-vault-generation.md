# D04: Vault Generation

**Effort:** M (4h)
**Phase:** Dungeons (Week 4)
**Dependencies:** D01, D05

---

## Summary

Vaults are locked rooms with high-value loot. Require lever to open gate.

---

## Scope

- [ ] `Vault` component for vault rooms
- [ ] Locked gate terrain (impassable until opened)
- [ ] Vault loot generation (better than normal)
- [ ] 1 vault per level (level 1+)

---

## Technical Details

### Component

```python
@component(slots=True, kw_only=True)
class Vault:
    level_eid: EntityId
    gate_positions: list[tuple[int, int]]
    opened: bool = False
    risk_level: int
```

### Gate Terrain

```python
TILE_GATE_CLOSED = 12  # impassable
TILE_GATE_OPEN = 13    # passable

WALKABLE |= {TILE_GATE_OPEN}
# TILE_GATE_CLOSED not in WALKABLE
```

### Generation

```python
def place_vault(level_eid: EntityId, room_pos: tuple, risk_level: int):
    # Place vault room with gate
    top = room_pos[0] * TILE_STRIDE_H
    left = room_pos[1] * TILE_STRIDE_W

    # Gate across entrance
    gate_positions = []
    for dx in range(4, 12):
        set_tile(level_eid, top + 10, left + dx, TILE_GATE_CLOSED)
        gate_positions.append((top + 10, left + dx))

    vault_eid = esper.create_entity(
        Vault(level_eid=level_eid, gate_positions=gate_positions, risk_level=risk_level),
    )

    # Place loot inside
    place_vault_loot(level_eid, top + 5, left + 8, risk_level)
```

### Vault Opening (D05 lever triggers this)

```python
def open_vault(vault_eid: EntityId):
    vault = esper.component_for_entity(vault_eid, Vault)
    vault.opened = True

    for y, x in vault.gate_positions:
        bus.pulse(bus.MutateTile(map_id=vault.level_eid, y=y, x=x, new_tile=TILE_GATE_OPEN))
```

---

## Acceptance Criteria

- [ ] Vault room with locked gate
- [ ] Gate blocks movement until opened
- [ ] Vault loot uses VAULT_LOOT table
- [ ] 1 vault per level on depth 1+
