# Core Systems Reference

Technical reference for current nightstorm, camp, stress, and experience implementations.

**For planned changes, see:** `docs/plans/2026-01-10-q1-mvp-design.md`

---

## Time System

### Real Time to Game Time

```
SECONDS_PER_NIGHT = 18 minutes (1080 seconds)
SECONDS_PER_NIGHTSTORM = 25 seconds
HOURS_PER_NIGHT = 20 (6am → 2am)
NIGHTS_PER_DAY = 80 (one real day = 80 game cycles)
```

### Daily Cycle

| Game Time | Phase | Real Duration |
|-----------|-------|---------------|
| 6am - 2am | Active day | ~17.5 minutes |
| 2am - 6am | Nightstorm | ~25 seconds |

### Key Properties (NightClock)

- `hour`, `minute` - Current game time
- `in_nightstorm` - Boolean, true during 2am-6am
- `nightstorm_eta` - Seconds until nightstorm begins
- `brightness_index` - 0-7 light level (0 during nightstorm)
- `dawn`, `dusk` - Seasonal sunrise/sunset times

---

## Nightstorm

### Current Implementation

**Location:** `ninjamagic/survive.py`

**Trigger:** `CoverCheck` signal fires ~1:50am, `RestCheck` fires at 2am.

**Current flow:**
1. Players not camping get "Take cover!" prompt
2. If they type "take cover" in time → `TookCover` component, partial protection
3. If they fail → full damage
4. At rest check: camping players rest, others take damage

**Current damage (not camping):**
```python
ROUGH_NIGHT_HEALTH = -75.0
ROUGH_NIGHT_STRESS = 100.0
ROUGH_NIGHT_AGGRAVATED = 100.0
```

**Current recovery (camping + ate):**
```python
REST_HEALTH = 45
REST_STRESS = -75
REST_AGGRAVATED_STRESS = -125
```

---

## Camp Mechanics

### Props and Stances

**Location:** `ninjamagic/component.py`, `ninjamagic/survive.py`

Players interact with "props" - entities they sit/lie at:
- `ProvidesHeat` - Campfires. Affects eating quality.
- `ProvidesLight` - Light sources. Affects eating quality.
- `Anchor` - Bonfires. Guarantees rest, removes need for survival contest.
- `ProvidesShelter` - Shelters. Affects rest quality away from anchor.

**Stance component:**
```python
class Stance:
    cur: Stances  # "standing", "kneeling", "sitting", "lying prone"
    prop: EntityId  # What they're sitting/lying at

    def camping(self) -> bool:
        # True if sitting or lying at a prop
```

### Eating

**Location:** `ninjamagic/survive.py:process_eating()`

Eating quality calculated as **pips** (sum of conditions):

| Condition | Pips | How to get |
|-----------|------|------------|
| `is_tasty` | 1 | Food level vs your highest skill rank |
| `is_very_tasty` | 1 | Higher food level contest |
| `is_resting` | 1 | Sitting or lying prone |
| `is_lit` | 1 | Prop has `ProvidesLight` OR brightness >= 6 |
| `is_warm` | 1 | Prop has `ProvidesHeat` |
| `is_safe` | 1 | Prop has `Anchor` OR survival vs hostility contest |
| `is_shared` | **4** | Another player at same prop |

**Total possible:** 10 pips (6 base + 4 shared)

**Stored in:** `Ate` component with `meal_level` and `pips`

### Resting

**Location:** `ninjamagic/survive.py:process_rest()`

**At anchor (bonfire):**
- Guaranteed rest
- `weariness_factor = 1.0`
- Sets `LastAnchorRest` timestamp

**Away from anchor:**
- Survival vs hostility contest
- Weariness accumulates based on nights since last anchor rest
- Can use `Sheltered` component for bonus
- `get_max_nights_away()` based on survival rank (currently returns 0 or 1)

**On successful rest:**
```python
bus.pulse(
    bus.HealthChanged(health_change=45, stress_change=-75, aggravated_stress_change=-125),
    bus.AbsorbRestExp(source=eid),
)
```

---

## Stress System

### Current Implementation

**Location:** `ninjamagic/component.py:Health`

```python
class Health:
    cur: float = 100.0           # Current health (0-100)
    stress: float = 0.0          # Current stress (0-200)
    aggravated_stress: float = 0.0  # Stress floor
    condition: Conditions = "normal"  # normal/unconscious/in shock/dead
```

**Key mechanics:**
- Stress recovers from resting, but not below `aggravated_stress`
- Aggravated stress only recovers from resting at anchor
- Currently no threshold effects at 100 or 200

---

## Experience System

### Overview

XP is earned throughout the day and consolidated at rest. The bonfire is where you grow.

### Learning (During Day)

**Location:** `ninjamagic/experience.py`

**Signal:** `bus.Learn(source, teacher, skill, mult)`

- `source` - Who is learning
- `teacher` - Entity that taught them (map, enemy, ally)
- `skill` - Which skill (martial_arts, evasion, survival)
- `mult` - Contest multiplier affecting XP amount

**On Learn signal:**
```python
award = Trial.get_award(mult=sig.mult)
skill.tnl += award  # Small immediate gain

# Store for consolidation
rest.gained[skill.name][sig.teacher] += award
```

### RestExp Component

**Location:** `ninjamagic/component.py:RestExp`

```python
class RestExp:
    # XP gained today, by skill name, by teacher entity
    gained: dict[str, dict[int, float]]

    # Bonus multipliers for skills not practiced
    modifiers: dict[str, float]
```

### Consolidation (At Rest)

**Location:** `ninjamagic/experience.py:process()` handling `AbsorbRestExp`

**Flow:**
1. For each skill, for each teacher:
   - Cap XP from any single teacher: `MAX_EXP_PER_ENTITY = 0.45`
   - Multiply by eating pips: `award *= ate.pips`
   - Multiply by skill modifier: `award *= rest.modifiers.get(name, 1)`
   - Add to skill's `tnl`

2. Skills NOT practiced get 1.8x modifier next cycle

3. Rank up when `tnl >= 1.0`:
   - `skill.rank += 1`
   - `skill.tnl -= 1`
   - `skill.tnl *= RANKUP_FALLOFF` (1/1.75)

### XP Sources

| Activity | Teacher | Skill |
|----------|---------|-------|
| Combat (attacking) | Enemy entity | Martial Arts |
| Combat (defending) | Enemy entity | Evasion |
| Foraging | Map entity | Survival |
| Eating in hostile area | Map entity | Survival |
| Resting away from anchor | Map entity | Survival |
| Cooking | (none) | Survival |

### Cooperation Bonus

**Shared eating = +4 pips**

This multiplies ALL RestExp consolidation. Two players eating together both get the bonus. This is the primary cooperation forcing function for XP.

**Fighting together:**
- Both players get Learn signals from same enemy
- Per-teacher cap (0.45) prevents one enemy from being infinite XP
- But fighting MORE enemies together = more teachers = more XP

---

## Signal Reference

### Nightstorm/Camp Signals

| Signal | When | Effect |
|--------|------|--------|
| `CoverCheck` | ~1:50am | Triggers cover prompts |
| `RestCheck` | 2am | Triggers rest resolution |
| `Eat` | Player eats food | Process eating, calculate pips |
| `HealthChanged` | Various | Modify health/stress/aggravated |
| `Cleanup` | After rest | Remove Ate, Sheltered, TookCover |

### Experience Signals

| Signal | When | Effect |
|--------|------|--------|
| `Learn` | During activity | Accumulate RestExp |
| `AbsorbRestExp` | At rest | Consolidate XP, rank up |

---

## File Reference

| File | Systems |
|------|---------|
| `nightclock.py` | Time, seasons, brightness |
| `survive.py` | Eating, cover, rest resolution |
| `experience.py` | Learn, consolidation, rank up |
| `component.py` | Health, Ate, RestExp, Anchor, etc. |
| `cook.py` | Cooking mechanics |
| `forage.py` | Foraging mechanics |
