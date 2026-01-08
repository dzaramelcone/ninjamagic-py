# T03: Fire Spread Core

**Effort:** M (4h)
**Phase:** Terrain (Week 1)
**Dependencies:** T01

---

## Summary

Create deterministic fire system. Server sends seed + origin; clients reconstruct spread locally. One packet per fire event, not per-cell updates.

---

## Current State

- `gas.py` implements spreading effect with heapq scheduling
- No fire system exists

---

## Scope

- [ ] Create `ninjamagic/fire.py` with deterministic spread algorithm
- [ ] Fire entity with seed, origin, tick count
- [ ] Client-reconstructible spread (same seed → same pattern)
- [ ] `CreateFire` signal sends minimal data (origin, seed, intensity)
- [ ] `FireTick` signal for tick advancement (just tick number)
- [ ] Client simulates spread locally from seed

---

## Technical Details

### Core Insight

Fire spread is deterministic given:
1. Origin tile (y, x)
2. Seed (int)
3. Terrain state at ignition time
4. Tick number

Client can reconstruct entire fire state from these 4 values.

### Fire Entity Structure

```python
@component(slots=True, kw_only=True)
class FireState:
    origin_y: int
    origin_x: int
    seed: int
    start_tick: int
    intensity: float = 0.8
```

### Signals (Minimal Network Payload)

```python
@signal(frozen=True, slots=True, kw_only=True)
class CreateFire(Signal):
    map_id: int
    y: int
    x: int
    seed: int
    intensity: float = 0.8

@signal(frozen=True, slots=True, kw_only=True)
class FireTick(Signal):
    fire_eid: EntityId
    tick: int

@signal(frozen=True, slots=True, kw_only=True)
class FireExtinguished(Signal):
    fire_eid: EntityId
```

### Deterministic Spread Algorithm

```python
def compute_fire_state(
    map_id: int,
    origin_y: int,
    origin_x: int,
    seed: int,
    tick: int,
    initial_intensity: float = 0.8,
) -> dict[tuple[int, int], float]:
    """Same inputs → same output on server and client."""
    rng = random.Random(seed)
    fire: dict[tuple[int, int], float] = {(origin_y, origin_x): initial_intensity}

    for _ in range(tick):
        fire = _step_fire(map_id, fire, rng)
        if not fire:
            break

    return fire


def _step_fire(map_id, fire, rng):
    new_fire = {}
    for (y, x), intensity in fire.items():
        intensity = max(0, intensity - DECAY_RATE)
        if intensity <= 0:
            continue

        new_fire[(y, x)] = new_fire.get((y, x), 0) + intensity

        if intensity >= SPREAD_THRESHOLD:
            neighbors = [(y-1, x), (y+1, x), (y, x-1), (y, x+1)]
            rng.shuffle(neighbors)  # deterministic with seeded RNG
            for ny, nx in neighbors:
                if is_flammable(get_tile_id(map_id, ny, nx)):
                    jitter = 0.9 + rng.random() * 0.2
                    new_fire[(ny, nx)] = new_fire.get((ny, nx), 0) + intensity * SPREAD_FACTOR * jitter

    return new_fire
```

### Network Protocol

```python
def encode_create_fire(sig: CreateFire) -> bytes:
    """13 bytes: msg_type(1) + map_id(4) + y(2) + x(2) + seed(4)"""
    return struct.pack(">BIHHI", MSG_FIRE_CREATE, sig.map_id, sig.y, sig.x, sig.seed)

def encode_fire_tick(sig: FireTick) -> bytes:
    """5 bytes: msg_type(1) + fire_eid(4)"""
    return struct.pack(">BI", MSG_FIRE_TICK, sig.fire_eid)
```

---

## Network Comparison

**Old approach (per-cell updates):**
- 100 burning cells × 8 bytes/cell = 800 bytes/tick
- 2 ticks/second = 1.6 KB/second per fire

**New approach (seed-based):**
- CreateFire: 13 bytes once
- FireTick: 5 bytes/tick
- 2 ticks/second = 10 bytes/second per fire
- **160x bandwidth reduction**

---

## Files

- `ninjamagic/fire.py` (new)
- `ninjamagic/bus.py` (add signals)
- `ninjamagic/state.py` (add to game loop)
- `ninjamagic/outbox.py` (fire packet encoding)
- `fe/src/svc/fire.ts` (client simulation)

---

## Open Design Questions

**Terrain mutation during spread:**
Fire burns grass → burned. If client checks current terrain, simulation diverges from server.

Current approach: fire spread pattern is fixed at ignition time (option 2). Fire spreads to where it "would" spread based on terrain snapshot, ignores newly-burned tiles.

**Simulation interactions:**
Fire + gas = explosion. Two simulations need consistent state. Options:
- Server runs ahead, batches events into timeline frames, client replays with slight delay
- Accept minor divergence, sync explosions as discrete events
- Simple simulations may not need full determinism - just sync the consequences (damage, mutations)

Needs design spike before implementation.

---

## Acceptance Criteria

- [ ] `CreateFire` signal spawns fire with seed
- [ ] Fire spread is deterministic (same seed → same pattern)
- [ ] Client can reconstruct fire state from seed + tick
- [ ] Network sends ~5 bytes per tick, not per-cell data
- [ ] Fire entity deleted when all intensity gone
- [ ] Test: create fire, verify server/client states match
- [ ] Design doc for simulation interactions (fire/gas/water)
