# T02: Tile Mutation

**Effort:** S (2h)
**Phase:** Terrain (Week 1)
**Dependencies:** T01

---

## Summary

Tiles can change at runtime. Fire burns grass to ash. Bridges collapse into chasms.

---

## Design

### The Need

Static terrain is boring. Dynamic terrain is Brogue. We need tiles to transform based on game events.

### Signal-Based Mutation

Follow the bus pattern. `MutateTile` signal requests a change. Mutation processor validates and applies it. `TileChanged` signal broadcasts the result for network sync.

Why signals? Decoupling. Fire system doesn't need to know about chunk storage. It just emits "this tile should burn."

### System Loop Position

Mutation runs **before move**. If a tile becomes unwalkable, we need to handle entities on it before they try to move.

### Validation

What if an entity is standing on a tile that becomes unwalkable?

- **Bridge → chasm**: Entity falls (damage, possibly death)
- **Ground → wall**: Block the mutation (shouldn't happen organically)
- **Shallow water → deep water**: Entity starts drowning

The mutation system must check for entities and handle consequences.

### Network Sync

Tile changes sync to clients as discrete events. Small packet: map_id, position, new tile ID. Client applies the change to its local chunk data.

---

## Acceptance Criteria

- [ ] `MutateTile` signal triggers tile change
- [ ] Mutation processor validates before applying
- [ ] Entities on mutating tiles are handled (damage, displacement)
- [ ] `TileChanged` signal syncs to clients
- [ ] Runs before `move` in system loop
