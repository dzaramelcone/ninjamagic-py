# Q1 Roadmap

**Goal:** Ship a minimum viable product that demonstrates the thesis—survive together or die alone—and begins growing a player base.

**Thesis:** Optimal play is cooperation. The systems should make this true through math, not morality.

---

## Tier 1: Ship-Blocking

Without these, the game doesn't work.

| # | Feature | Effort | Why |
|---|---------|--------|-----|
| 1 | **Night mobs** | L | No threat = no cooperation pressure. Spawn creatures during nightstorm. 25 seconds of hell, ease in. |
| 2 | **Weapons + armor wired** | M | Combat is flat with fists only. Armor code exists (armor.py), wire it to combat.py. Add knife/club/spear. |
| 3 | **Death stakes** | S | Drop items on death. Currently death is consequence-free. |
| 4 | **`give` command** | S | One command. Foundation for sharing, trading, cooperation dynamics. |
| 5 | **Tutorial prompts** | M | Contextual hints for newbies. "Type `attack goblin`". Toggleable. |
| 6 | **Newbie XP curve** | S | Fast ranks early, interpolate bonus down after rank 50. Hook before quit. |
| 7 | **Keystroke capture** | S | Ship data collection with prompts. Timestamps, deltas. Anti-cheat foundation. |

---

## Tier 2: Ship With

High value, reasonable effort, or unblocks future work.

| # | Feature | Effort | Why |
|---|---------|--------|-----|
| 8 | **Nightstorm rework** | M | Remove `take cover` prompt. Danger relative to area. Spawn mobs, lengthy stun. Custom scenarios later. |
| 9 | **Persistence** | L | World/player state survives restart. Non-negotiable for real players. |
| 10 | **Aliases** | M | `alias k attack`. Saved to account. Reduces typing friction. |
| 11 | **Respawn fix** | S | The HACK at combat.py:233. Stateful respawn is fragile. |
| 12 | **Map tile deltas** | M | Gas sends too many packets. General solution: only send changes. |

---

## Tier 3: DX & Polish

Unblocks velocity. Ship with or immediately after.

| # | Feature | Effort | Why |
|---|---------|--------|-----|
| 13 | **VS Code debugger** | S | launch.json for uvicorn with attached debugger. |
| 14 | **Local test login** | S | Smooth character switching for testing. |
| 15 | **Parser alias system** | S | The TODO at parser.py:14. Powers user aliases (#10). |
| 16 | **Visibility optimization** | M | The TODO at visibility.py:230. Will matter with more entities. |

---

## Tier 4: Post-Launch Iteration

Cool but not MVP. Some need player data first.

| Feature | Notes |
|---------|-------|
| **Fight profiles** | Track yomi patterns. Need combat data to analyze. |
| **Typing fingerprints** | Anti-cheat detection layer. Need baseline data (Tier 1 #7). |
| **AI players/agents** | Design requirements spec'd. Build after core loop proven. |
| **Character creation TUI** | BG3-style. Simple name+pronouns is fine for MVP. |
| **Town growth** | Kingdom-style development. Need players first. |
| **Player guilds** | Let players self-organize, then formalize what emerges. |
| **Mouse inventory** | Clicks → commands. Nice UX, not blocking. |
| **Ingredient chains** | Sap → syrup. Cooking works, iterate later. |
| **Shelter building** | Meaningful after night mobs exist. |
| **Fire maintenance** | Same. After night mobs. |
| **Smart entity pointers** | ECS refactor. Do when pattern is clear. |
| **More combat verbs** | Feint, grab, kick, dodge. After core yomi proven. |

---

## Code TODOs (from codebase)

Prioritized for MVP relevance:

| Priority | Location | Issue |
|----------|----------|-------|
| **HIGH** | combat.py:233 | Respawn HACK - fragile if disconnect at 60s mark |
| **HIGH** | parser.py:14 | Alias system needed for user aliases |
| **HIGH** | visibility.py:230 | "optimize lol" - will matter with mobs |
| **MED** | combat.py:60 | Move target validation earlier |
| **MED** | forage.py:37 | Nested containment validation (use-after-free risk) |
| **MED** | survive.py:254 | Survival vs area for take cover mult (removing anyway) |
| **LOW** | experience.py:72 | Rank-up calc could be clientside |
| **LOW** | forage.py:33 | Tile-specific forage tables |
| **LOW** | forage.py:50 | Fermentation instead of rotting |
| **LOW** | forage.py:116 | Gradual rot instead of binary |
| **LOW** | conn.py:18 | Reconceptualize connection binding |
| **LOW** | armor.py:32 | Armor dataclass cleanup |
| **LOW** | armor.py:45 | mitigate() signature cleanup |
| **LOW** | cook.py:22 | Decouple cooking messages from story |
| **LOW** | echo.py:16 | Some reaches don't need origin |
| **LOW** | util.py:21 | RNG/LOOP global cleanup |

---

## Timeboxed Schedule

### Week 1-2: Combat Foundation
- [ ] Wire armor.py to combat.py
- [ ] Add weapons (knife, club, spear) with different timings
- [ ] Death drops items
- [ ] `give <item> to <player>` command

### Week 3-4: Night Threat
- [ ] Night mob spawning during nightstorm
- [ ] Mob AI (hunt players, flee at dawn)
- [ ] Remove `take cover` prompt
- [ ] Area danger affects nightstorm severity

### Week 5: Onboarding
- [ ] Tutorial prompt system (contextual hints)
- [ ] Newbie XP bonus curve
- [ ] Keystroke capture in prompts

### Week 6: Polish & Persistence
- [ ] Player/world persistence (postgres)
- [ ] Respawn fix (combat.py HACK)
- [ ] Map tile delta packets

### Week 7: QoL
- [ ] Alias system (parser + account storage)
- [ ] VS Code debugger launch config
- [ ] Local test login cleanup

### Week 8: Buffer
- [ ] Playtest
- [ ] Bug fixes
- [ ] Performance (visibility optimization)
- [ ] Soft launch prep

---

## AI Integration Design (Future)

### Agent Capabilities
```
move(direction) / move_to(location)
attack(target) / block()
say(message) / emote(action)
forage() / eat(item) / cook(items)
give(item, target) / take(item)
rest() / camp()
perceive() → nearby entities, time, health, inventory
```

### Constraints
- Same action timing as players
- Same visibility (fog of war)
- Personality weights decisions
- Can die, can respawn

### Quest System
- Agents have goals (collect, protect, hunt)
- Goals → behavior → emergence
- No dialogue trees—dynamic response

---

## Success Metrics

**Week 8 launch criteria:**
- [ ] Players can survive the night (with cooperation)
- [ ] Players can die (and it matters)
- [ ] Players can share (and it's optimal)
- [ ] New players can learn (without wiki)
- [ ] Server survives restart (persistence)
- [ ] Combat has depth (weapons, armor, yomi)

**Post-launch signals:**
- Retention: Do players come back?
- Session length: Do they stay?
- Social: Do they cooperate?
- Word of mouth: Do they invite friends?

---

## Cut List

Explicitly not doing for MVP:
- ~~Reputation system~~ (let it emerge from player memory)
- ~~Weather variation~~ (nightstorm is enough)
- ~~Skills expansion~~ (3 skills is fine)
- ~~Procedural generation~~ (handcraft first areas)
- ~~Factions~~ (let players self-organize)
- ~~Rich character creation~~ (name + pronouns works)
- ~~Magic~~ (keep it grounded)
