# D14: Prefab Expansion

**Effort:** M (4h)
**Phase:** Dungeons (Week 3-4)
**Dependencies:** D01, D04, D07

---

## Summary

Expand room prefabs for dungeon themes. Vault rooms, terrain rooms, special features.

---

## Scope

- [ ] Vault room prefabs
- [ ] Water pool room prefabs
- [ ] Swamp room prefabs
- [ ] Magma room prefabs
- [ ] Bridge corridor prefabs
- [ ] Feature placement markers in prefabs

---

## Technical Details

### Prefab Format

```python
@dataclass(frozen=True)
class Prefab:
    layout: str
    legend: dict[str, int]
    features: dict[str, str]
    min_risk: int = 0

BASE_LEGEND = {
    ".": TILE_STONE_FLOOR,
    "#": TILE_STONE_WALL,
    "~": TILE_DUNGEON_WATER_SHALLOW,
    "≈": TILE_DUNGEON_WATER_DEEP,
    "%": TILE_DUNGEON_SWAMP,
    "=": TILE_BRIDGE,
    "_": TILE_CHASM,
    "*": TILE_MAGMA,
    "+": TILE_GATE_CLOSED,
}

FEATURE_MARKERS = {
    "C": "chest",
    "V": "vault",
    "L": "lever",
    "D": "den",
    "B": "barrel",
    "T": "trap",
}
```

### Vault Prefab

```python
VAULT_ROOM = Prefab(
    layout="""
################
#..............#
#.############.#
#.#..........#.#
#.#....VV....#.#
#.#..........#.#
#.############.#
#......++......#
################
""",
    legend=BASE_LEGEND,
    features={"V": "vault"},
    min_risk=20,
)
```

### Prefab Selection

```python
def select_prefab(room_type: DungeonRoomType, risk_level: int) -> Prefab | None:
    candidates = ROOM_PREFABS.get(room_type, [])
    valid = [p for p in candidates if p.min_risk <= risk_level]
    return RNG.choice(valid) if valid else None
```

---

## Acceptance Criteria

- [ ] Prefab data structure with layout + legend + features
- [ ] Vault, water, swamp, magma room prefabs
- [ ] Bridge corridor prefab
- [ ] Feature markers place entities correctly
