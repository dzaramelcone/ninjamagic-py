# T09: Swamp Gas Emission

**Effort:** S (2h)
**Phase:** Terrain (Week 3)
**Dependencies:** T01

---

## Summary

Swamp tiles emit gas over time, creating explosive hazards.

---

## Scope

- [ ] Swamp tiles periodically emit gas
- [ ] Gas accumulates and spreads (existing gas.py)
- [ ] Tie into fire-gas explosion (T05)

---

## Technical Details

```python
# gas.py or swamp.py
SWAMP_EMIT_RATE = 5.0  # seconds between emissions
SWAMP_EMIT_AMOUNT = 0.3

def process_swamp_emission(now: Looptime):
    for map_eid, chips in esper.get_component(Chips):
        for (cy, cx), grid in chips.dict.items():
            for idx, tile_id in enumerate(grid):
                if not emits_gas(tile_id):
                    continue

                y = cy * TILE_STRIDE_H + idx // TILE_STRIDE_W
                x = cx * TILE_STRIDE_W + idx % TILE_STRIDE_W

                # Emit gas at this tile
                if should_emit(now, y, x):
                    bus.pulse(bus.CreateGas(
                        map_id=map_eid,
                        y=y, x=x,
                        amount=SWAMP_EMIT_AMOUNT,
                    ))
```

---

## Acceptance Criteria

- [ ] Swamp tiles emit gas periodically
- [ ] Gas accumulates in swamp areas
- [ ] Gas spreads using existing diffusion
- [ ] Fire ignites swamp gas (via T05)
