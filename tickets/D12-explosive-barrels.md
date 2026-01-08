# D12: Explosive Barrels

**Effort:** S (2h)
**Phase:** Dungeons (Week 4)
**Dependencies:** T03, T05, D01

---

## Summary

Barrels full of volatile liquid. Fire + barrel = boom.

---

## Design

### The Classic

Every dungeon crawler has explosive barrels. They're an environmental weapon - a loaded gun you can trigger from a distance.

"Lure enemies near barrels. Light the trail of grass. Run."

### Mechanics

Barrel is an entity. When fire reaches it:
1. Explosion deals area damage (falls off with distance)
2. Fire spawns in explosion radius
3. Barrel is destroyed

Chain reactions: explosion spawns fire → fire reaches another barrel → another explosion. Cascading doom.

### Placement

Barrels near choke points. Near dens. Near valuable loot. They're risk/reward - the thing that makes a room dangerous is also what can clear it.

### Player Agency

Players can:
- Ignite barrels to clear enemies
- Avoid barrels to preserve escape routes
- Push enemies toward barrels (if we have knockback)
- Use barrels against each other in PvP

---

## Acceptance Criteria

- [ ] Barrel entities placed in dungeons
- [ ] Fire contact triggers explosion
- [ ] Explosion deals AoE damage
- [ ] Explosion spawns fire in radius
- [ ] Barrel destroyed after explosion
