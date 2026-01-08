# T07: Fire Network + Render

**Effort:** M (4h)
**Phase:** Terrain (Week 2)
**Dependencies:** T03

---

## Summary

Client receives fire state from server and renders it.

---

## Design

### Network Flow

Server sends fire state updates. Client receives and stores them. On render, client draws fire at the appropriate cells.

With Q1's server-authoritative approach (T03), client just renders what server tells it. No local simulation needed.

### Fire State on Client

Client needs to track:
- Which cells are on fire
- Intensity at each cell (for visual brightness)
- When fire is extinguished (cleanup)

### Rendering

Fire rendering options:
- **Simple**: colored rectangles with alpha based on intensity
- **Better**: animated sprites, particle effects
- **Best**: WebGL shader with procedural flicker

Start simple. Colored rectangles with random flicker. Ship it. Polish later if players care.

### Flicker

Fire should flicker. Random intensity variation each frame makes it feel alive. This is purely cosmetic - doesn't affect gameplay state.

---

## Acceptance Criteria

- [ ] Client receives fire state from server
- [ ] Fire renders at correct cells
- [ ] Intensity affects visual brightness
- [ ] Fire flickers (cosmetic animation)
- [ ] Fire disappears when extinguished
