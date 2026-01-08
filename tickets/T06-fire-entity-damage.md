# T06: Fire Entity Damage

**Effort:** S (2h)
**Phase:** Terrain (Week 2)
**Dependencies:** T03

---

## Summary

Standing in fire hurts. Armor type matters.

---

## Design

### Damage Over Time

Entities in fire take damage each tick. Damage scales with fire intensity - the hotter the fire, the more it hurts.

### Armor Interaction

Different armor types interact with fire differently:

- **Plate armor** - conducts heat, amplifies fire damage (you're cooking inside)
- **Leather armor** - neutral, standard damage
- **Cloth/magical** - can resist fire (enchanted robes, wet cloth)

This creates tactical decisions. Full plate makes you a tank against swords but vulnerable to fire. The enemy in heavy armor? Lure them through flames.

### Feedback

Players need to know they're burning:
- "You are burning!" message
- Visual effect on character
- Damage numbers

Clear feedback lets players make informed decisions about staying vs fleeing.

---

## Acceptance Criteria

- [ ] Entities in fire take damage per tick
- [ ] Damage scales with fire intensity
- [ ] Armor type modifies damage (plate amplifies, cloth can resist)
- [ ] Player receives burning feedback message
