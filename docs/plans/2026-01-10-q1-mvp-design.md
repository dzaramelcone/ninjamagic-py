# Q1 MVP Design

## Goal

Q1 MVP is a public release that conveys how this game pushes the genre and begins building a playerbase.

**What we're pushing:**
- Text-based/MUD/ASCII roguelike genres are beautiful, and they're dying
- We resurrect them through multiplayer emergent dynamics
- The game IS the thesis: player investment holds back entropy
- Few players = small claim. Many players = civilization. The world literally can't grow without community.

**The genre statement:** This is a beautiful genre, and it's dying. Just like the world you're in. Your presence is what keeps it alive.

---

## The Mood

The world is dark, fading, could go. Players huddle together against infinite darkness. There's something beautiful in the presence, the togetherness. Hopeless, but not despair - warmth against the cold.

**Emotional arc per session:**
1. Dread - night is coming
2. Relief - I made it back
3. Gratitude - I wouldn't have made it alone
4. Presence - the world is fading, but we're here together

The presence beat is the heart. It lives in the 1am-dawn stretch - after waves fade, eating together, resting, just being at the fire.

---

## Q1 Spikes

Two spikes, two sides of the same coin:

| Spike | Purpose |
|-------|---------|
| **The Darkness** | What entropy does. The threat. |
| **World State** | What players do about it. The response. |

**Deferred to Q2:**
- Stress thresholds / demon powers (temptation beat)
- Lost state / rescue mechanics

---

## Spike 1: The Darkness

**Core principle:** Darkness is entropy. Everything changes, decays, shifts in the dark. The darkness is infinite and pushes back harder the more you claim.

### Mobs

**Spawn behavior:**
- Mobs spawn from unlit tiles (outside anchor radius)
- Path toward nearest anchor
- Spawn rate increases at night, peaks during wave hours (11pm-1am)

**Phenotypes:**

| Type | Composition | Experience | Priority |
|------|-------------|------------|----------|
| Swarm | Many weak units | Dopamine fiesta - mow them down | Q1 core |
| Pack | Coordinated group, mixed threats | Context switching, target prioritization | Q1 core |
| Death Knight | Single mob, matched to your strength | 1v1 duel, skill test | Q1 core |
| Special Encounter | Boss + adds (lich + swarms, kaiju) | Event, memorable moment | Q1 core |
| Invader | Agentic AI, yomi-focused | From-style mind game | Q1 stretch |

### Terrain Decay

- **Lazy instantiation** - terrain generates on first visit
- **Decay begins immediately** - the moment it exists, entropy starts
- **Decay rate = f(distance from anchors)** - further from light = faster decay
- **Special action stops decay** - ties into World State (anchors, investment)

**Decay effects:**
- Paths overgrow, become difficult terrain
- Resources deplete or spoil
- Landmarks shift (disorientation)

**Rate:** Slow enough to venture out during day, fast enough that nothing persists without light.

---

## Spike 2: World State

**Core principle:** Light is stability. Player investment creates permanence. The only way to hold back entropy is presence and sacrifice.

### Anchor Creation

**The Pilgrimage:**

1. **Kneel at existing anchor** - you need an anchor to make an anchor (chain of light)
2. **Calibrate sacrifice** - choose what to give up (XP, health, treasured item)
3. **Create sacrifice item** - your sacrifice becomes an object you carry
4. **Enter pilgrimage state** - glass cannon:
   - Demon empowered: 1-2 special procs/verbs (Q2 preview)
   - Stress rapidly accelerates
   - More fragile, take more damage
   - **If you die: sacrifice item lost, sacrifice wasted**
5. **Reach destination** - build bonfire at new location
6. **Place sacrifice item in bonfire** - anchor is born

**Origin:** One eternal anchor exists (the genesis point). All light chains from there.

### Anchor Strength

Bigger sacrifice = stronger anchor:
- Larger stability radius
- Slower base decay rate
- More resilient to neglect

### Anchor Maintenance

- **Fuel** - wood, oil, gathered resources
- **Tending** - player actions (stoke fire, etc.)
- **Presence** - decay slows with players nearby
- **Character level** - higher level = more maintenance capacity

### Soft Scaling

- Decay rate = f(distance from players, anchor strength, total anchors maintained)
- One player CAN hold many anchors, but barely
- More players = easier maintenance = more territory possible

### Territory Loss

- Gradual, not instant
- Strong settlements have strong TD
- TD failures damage structures, don't instantly wipe
- Eventually can be lost if neglected
- Permanent until pilgrimage creates new anchor

---

## The Loop

| Time | Phase | Darkness Does | Players Do |
|------|-------|---------------|------------|
| 6am-6pm | Day | Mobs roam (manageable), decay ticks | Venture out, forage, fight, pilgrimage |
| 6pm-11pm | Evening | Tension rises, decay accelerates | Head back, cook, eat together |
| 11pm-1am | Waves | Mobs path toward anchors, peak pressure | Defend the light together |
| 1am-2am | Fade | Waves die off | Eat, prepare to rest |
| 2am-dawn | Rest | Darkness pauses | Camp triggers, XP consolidates |

**The success case:** Well-prepared group handles waves by 1am, shares a meal, rests comfortably. Maybe tomorrow they expand.

**The failure case:** Still fighting at 2am, miss camp window, stress accumulates, no XP consolidation. Anchors decay. Territory shrinks.

**The mood:** Night after night, holding a small circle of light against infinite dark. Sometimes you grow. Sometimes you lose ground. But you're together.

---

## Progression

Follows Kingdom / A Dark Room / roguelike patterns:
- Investment in structures = stronger settlements
- XP = stronger character
- Itemization = better gear
- Metaprogression across sessions
- Live the character fantasy more richly over time

---

## Success Criteria

**The MVP succeeds when:**

- [ ] Night feels dangerous (mobs spawn from darkness, waves hit, decay threatens)
- [ ] Anchors feel precious (sacrifice to create, effort to maintain, loss hurts)
- [ ] Cooperation is obviously optimal (can't hold much alone, more hands = more territory)
- [ ] The presence moment lands (1am-dawn feels like a huddle against the dark)
- [ ] Players want to return (progression feels meaningful, territory grows, character grows)

**The test:** Two strangers meet at the eternal anchor. Survive nights together. Expand. Lose ground. Hold what matters. Feel something.
