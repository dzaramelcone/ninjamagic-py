# Q1 Roadmap

**Goal:** Ship a multiplayer Brogue. The environment is a weapon. Every fight asks "can I use the terrain?"

**Thesis:** Optimal play is cooperation. The systems make this true through physics, not morality.

---

## The Brogue Thesis

Emergence from transparent systems:
- Fire spreads to dry grass, ignites gas, burns bridges
- Water conducts, extinguishes, drowns
- Gas diffuses, explodes, obscures
- Terrain is destructible, buildable, weaponizable

Players don't need to be told "cooperate." The systems make it obvious.

---

## Phase 1: Terrain (Weeks 1-2)

The environment as character.

### Terrain Types

| Terrain | Walk | Interactions |
|---------|------|--------------|
| **Ground** | ✓ | Default |
| **Wall** | ✗ | Destructible, blocks LOS |
| **Grass** | ✓ | Burns → ground |
| **Dry grass** | ✓ | Burns fast, spreads far |
| **Water shallow** | ✓ | Extinguish, slow, conduct |
| **Water deep** | ✓ | Drown, drop items, hide creatures |
| **Swamp** | ✓ | Emit gas, slow |
| **Chasm** | ✗ | Fall damage, drop level |
| **Bridge** | ✓ | Burns → chasm |
| **Magma** | ✗ | Ignite adjacent, light source |
| **Foliage** | ✓ | Hide, burn, regrow |

### Fire System

Extend `gas.py` pattern:

```python
# Fire spreads like gas but modifies terrain
Fire.intensity: dict[tuple[int,int], float]

# Each tick:
# - Spread to adjacent flammable
# - Decay intensity
# - intensity > 0.9 → spawn smoke
# - Fire + gas → explosion
# - Fire + water → steam
# - Fire + bridge → collapse after threshold
```

### Tasks
- [ ] TerrainType dataclass with properties
- [ ] Fire as effect layer (like gas)
- [ ] Fire spread to flammable terrain
- [ ] Fire + gas = explosion (AoE damage)
- [ ] Fire + water = steam (vision block)
- [ ] Bridge collapse mechanic
- [ ] Swamp emits flammable gas
- [ ] Water extinguishes, slows movement

---

## Phase 2: Dungeons (Weeks 3-4)

Procedural content that refreshes.

### Discovery

```python
# Player enters unexplored wilderness:
if not tile.explored and RNG.random() < discovery_chance:
    dungeon = generate_dungeon(depth=area_difficulty)
    spawn_entrance(tile, dungeon)
```

### Dungeon Features

| Feature | Description |
|---------|-------------|
| **Vault** | Locked room, treasure inside |
| **Trap** | Pit, dart, gas vent, pressure plate |
| **Lever** | Opens/closes gates |
| **Gate** | Blocks passage until lever/key |
| **Cage** | Contains creature, releases on open/break |
| **Monster den** | Spawn point, clearing = safe zone |
| **Explosive barrel** | Fire/damage → boom |

### Generation

Already have `simple.py` with prefab rooms. Extend:
- [ ] DungeonEntrance entity on overworld
- [ ] Dungeon as separate map (nested Transform)
- [ ] 1-3 depth levels
- [ ] Loot tables per depth
- [ ] Trap placement
- [ ] Gate/lever connections
- [ ] Monster den spawning

### World Regeneration

During nightstorm, far from bonfire:
- Foliage regrows
- Creatures respawn
- Dungeon loot refreshes (if empty)
- Terrain damage heals

---

## Phase 3: Stats & Chargen (Week 5)

Investment before first death.

### Stats → Mechanics

| Stat | Effects |
|------|---------|
| **Grace** | Evasion cap (50 + grace×2), move speed (±20%), swim/climb |
| **Grit** | Health cap (100 ± 50), carry weight, fire/poison resist |
| **Wit** | Trap detection, craft quality (±50%), XP mult (±10%) |

### Allocation
- Base: 10 each
- Chargen: +15 to distribute
- Soft cap: diminishing above 20
- Hard cap: 30

### Character Creation TUI

```
┌─────────────────────────────────────────┐
│  Name: [_______________]                │
│  Pronouns: (•) she  ( ) he  ( ) they    │
│                                         │
│  Appearance: [@] ███ Hue ████░░░░       │
│                                         │
│  ─── Stats (15 points) ───              │
│  Grace [████████░░░░░░░░░░░░] 18        │
│    → Evasion cap: 86, Move: +16%        │
│  Grit  [██████░░░░░░░░░░░░░░] 14        │
│    → Health: 120, Carry: 24             │
│  Wit   [██████░░░░░░░░░░░░░░] 13        │
│    → Traps: 13, XP: +3%                 │
│                                         │
│  [< Back]              [Create →]       │
└─────────────────────────────────────────┘
```

### Tasks
- [ ] Wire Stats to evasion/health caps
- [ ] Grace affects movement speed
- [ ] Grit affects carry capacity
- [ ] Wit affects trap detection radius
- [ ] Chargen UI with sliders
- [ ] Appearance: glyph + HSV color picker
- [ ] Preview stat effects in real-time
- [ ] Persist to database

---

## Phase 4: Night & Mobs (Week 6)

25 seconds of hell.

### Mob Types

| Creature | Behavior | Threat |
|----------|----------|--------|
| **Goblin** | Pack tactics, loot corpses | Low |
| **Wolf** | Track wounded, pack howl | Medium |
| **Crawler** | Ambush from water/foliage | Medium |
| **Shambler** | Slow, tough, swamp spawn | Medium |
| **Wraith** | Fast, phases walls at night | High |

### Spawning

```python
# Nightstorm (25 sec), intensity ramps 0→1→0
for tile in world:
    if distance_to_bonfire(tile) > SAFE_RADIUS:
        threat = tile.hostility * nightstorm_intensity
        spawn_mobs(tile, threat)
```

### Mob AI

```python
class MobBehavior:
    def process(self, mob, players, terrain):
        if health_low: flee_to_den()
        elif player_nearby: attack()
        elif night: hunt_toward_players()
        else: patrol_territory()
```

### Tasks
- [ ] Remove `take cover` prompt
- [ ] Nightstorm intensity curve (ease in/out)
- [ ] Mob spawning by distance from bonfire
- [ ] Basic mob AI (hunt/flee/patrol)
- [ ] Mob death drops loot
- [ ] Area-specific mob tables
- [ ] Den entities that spawn mobs

---

## Phase 5: Combat & Items (Week 7)

Weapons as timing.

### Weapons

| Weapon | Windup | Damage | Special |
|--------|--------|--------|---------|
| **Fist** | 3.0s | 1.0x | Always available |
| **Knife** | 1.5s | 0.7x | Bleed proc |
| **Club** | 4.0s | 1.5x | Stun proc |
| **Spear** | 2.5s | 1.0x | 2-tile reach |
| **Torch** | 2.0s | 0.5x | Ignite target |

Different timings = different yomi reads.

### Armor

Wire `armor.py` to `combat.py`:
```python
if armor := esper.try_component(target, Armor):
    damage *= armor.mitigate(weapon.type)
```

### Death Stakes

- Drop equipped items on death
- Skill decay? (lose % of highest skill)
- Respawn at bonfire, naked

### Tasks
- [ ] Weapon component with timing/damage/proc
- [ ] Wire armor mitigation
- [ ] `give <item> to <player>`
- [ ] Death drops items
- [ ] Torch weapon (ignites on hit)
- [ ] Spear reach (2-tile attack)

---

## Phase 6: Polish (Week 8)

Ship it.

### Onboarding
- [ ] Tutorial prompts (contextual hints)
- [ ] Newbie XP curve (fast early, slow after rank 50)
- [ ] Keystroke capture for anti-cheat

### QoL
- [ ] Aliases saved to account
- [ ] Map tile delta packets (perf)
- [ ] Respawn fix (combat.py:233 HACK)
- [ ] Visibility optimization

### DX
- [ ] VS Code debugger launch config
- [ ] Local test login cleanup

---

## Week 9: Buffer

- [ ] Playtest with fresh eyes
- [ ] Balance: mob difficulty, terrain damage, XP rates
- [ ] Bug fixes
- [ ] Launch

---

## Technical Specs

### Terrain Data

```python
@component(slots=True, frozen=True)
class TerrainType:
    walkable: bool = True
    flammable: bool = False
    burns_to: int | None = None
    blocks_los: bool = False
    movement_cost: float = 1.0
    water_depth: int = 0  # 0/1/2
    emits_gas: str | None = None

TERRAIN = {
    1: TerrainType(),  # ground
    2: TerrainType(walkable=False, blocks_los=True),  # wall
    3: TerrainType(water_depth=1, movement_cost=1.5),  # shallow
    4: TerrainType(flammable=True, burns_to=1),  # grass
    5: TerrainType(emits_gas="swamp", movement_cost=1.3),  # swamp
    6: TerrainType(flammable=True, burns_to=7),  # bridge
    7: TerrainType(walkable=False),  # chasm
}
```

### Dungeon Structure

```python
@component(slots=True)
class DungeonEntrance:
    dungeon_map_id: EntityId
    depth: int
    discovered_by: set[CharacterId]

# Player enters → Transform.map_id = dungeon_map_id
# Dungeons are maps with own Chips, Hostility, ForageEnvironment
```

### Effect Layers

```python
# Parallel to gas.py
class EffectLayer:
    """Fire, ice, poison, etc."""
    values: dict[tuple[int,int], float]
    spread_rate: float
    decay_rate: float

    def process(self, now, terrain, entities):
        # Spread, decay, interact with terrain/entities
```

---

## AI Integration (Post-Launch)

### Agent Tools
```
perceive() → entities, terrain, threats
move(direction)
attack(target) / block() / flee()
use(item) / give(item, target)
say(message)
```

### Agent Goals
- Survive (flee when low, seek food)
- Hunt (track players, attack)
- Guard (patrol area, attack intruders)
- Quest (collect X, deliver to Y)

### Constraints
- Same timing as players (no superhuman speed)
- Same vision (fog of war)
- Personality affects risk tolerance

---

## Success Criteria

**Launch when:**
- [ ] Fire spreads and chains (grass → gas → explosion)
- [ ] Dungeons generate with traps, loot, mobs
- [ ] Night spawns mobs, world regenerates
- [ ] Stats matter (visible in chargen, felt in gameplay)
- [ ] Death costs (drop items, skill decay)
- [ ] Cooperation is optimal (shared fire, mob fighting)

**The test:** Two strangers meet at bonfire. Survive night. Explore dungeon. Want to return.

---

## NOT Doing

- ~~Complex crafting~~ (torch, bandage, that's it)
- ~~Magic~~ (grounded survival)
- ~~Procedural overworld~~ (handcraft hub)
- ~~Factions~~ (emergent from players)
- ~~Quest NPCs~~ (AI agents later)
- ~~Dialogue trees~~ (say what you mean)

---

## Code TODOs (Prioritized)

| Pri | Location | Issue |
|-----|----------|-------|
| **P0** | combat.py:233 | Respawn HACK |
| **P0** | parser.py:14 | Alias system |
| **P0** | visibility.py:230 | Optimize for mobs |
| **P1** | forage.py:37 | Containment validation |
| **P1** | combat.py:60 | Target validation order |
| **P2** | forage.py:33 | Tile-specific forage |
| **P2** | forage.py:116 | Gradual rot |
