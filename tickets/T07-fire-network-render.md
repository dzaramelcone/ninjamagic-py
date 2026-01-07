# T07: Fire Network + Render

**Effort:** M (4h)
**Phase:** Terrain (Week 2)
**Dependencies:** T03

---

## Summary

Client-side fire rendering from seed-based reconstruction.

---

## Scope

- [ ] Client receives CreateFire packet
- [ ] Client stores fire seed/origin/tick
- [ ] Client reconstructs fire state each frame
- [ ] WebGL fire rendering (shader or sprites)
- [ ] Fire flicker animation

---

## Technical Details

### Client Fire Service

```typescript
// fe/src/svc/fire.ts
class FireService {
  private fires: Map<number, FireState> = new Map();

  onCreateFire(eid: number, mapId: number, y: number, x: number, seed: number) {
    this.fires.set(eid, { mapId, originY: y, originX: x, seed, tick: 0 });
  }

  onFireTick(eid: number) {
    const state = this.fires.get(eid);
    if (state) state.tick++;
  }

  getFireCells(mapId: number): Map<string, number> {
    const cells = new Map();
    for (const [eid, state] of this.fires) {
      if (state.mapId !== mapId) continue;
      const fireCells = computeFireState(state);
      for (const [key, intensity] of fireCells) {
        cells.set(key, (cells.get(key) || 0) + intensity);
      }
    }
    return cells;
  }
}
```

### Fire Rendering

```typescript
// fe/src/render/fire.ts
function renderFire(ctx: CanvasRenderingContext2D, cells: Map<string, number>) {
  for (const [key, intensity] of cells) {
    const [y, x] = key.split(",").map(Number);
    const alpha = Math.min(1, intensity);
    const flicker = 0.8 + Math.random() * 0.2;

    ctx.fillStyle = `rgba(255, ${100 + Math.random() * 50}, 0, ${alpha * flicker})`;
    ctx.fillRect(x * TILE_W, y * TILE_H, TILE_W, TILE_H);
  }
}
```

---

## Acceptance Criteria

- [ ] Fire appears on client when CreateFire received
- [ ] Fire animation updates each tick
- [ ] Fire flickers visually
- [ ] Fire disappears when FireExtinguished received
- [ ] Multiple overlapping fires render correctly
