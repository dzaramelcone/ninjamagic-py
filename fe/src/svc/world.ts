// src/svc/world.ts
import type { Chip } from "../gen/messages";

const CHUNK_WIDTH = 16;
const CHUNK_HEIGHT = 16;

interface ChipData {
  char: string;
  color: { h: number; s: number; v: number };
}

type ChipSet = {
  [chipId: string]: ChipData;
};

type TileKey = string;
type CoordKey = string;

function makeTileKey(top: number, left: number): TileKey {
  return `${top},${left}`;
}

function makeCoordKey(x: number, y: number): CoordKey {
  return `${x},${y}`;
}

function parseCoordKey(key: CoordKey): { x: number; y: number } {
  const [xs, ys] = key.split(",");
  return { x: Number(xs), y: Number(ys) };
}

interface MapData {
  id: number;
  data: Map<TileKey, Uint8Array>;
  gas: Map<TileKey, Float32Array>;
}

class World {
  private seen: Map<number, Set<string>> = new Map();
  private gasStaging: Map<number, Map<CoordKey, number>> = new Map();
  private gasPrevCoords: Map<number, CoordKey[]> = new Map();
  private gasFlushHandle: number | undefined;
  private gasClearTimer: number | undefined;

  private getSeenSet(mapId: number): Set<string> {
    let s = this.seen.get(mapId);
    if (!s) {
      s = new Set<string>();
      this.seen.set(mapId, s);
    }
    return s;
  }

  public markSeen(mapId: number, x: number, y: number): void {
    const s = this.getSeenSet(mapId);
    s.add(makeCoordKey(x, y));
  }

  public wasSeen(mapId: number, x: number, y: number): boolean {
    const s = this.seen.get(mapId);
    if (!s) return false;
    return s.has(makeCoordKey(x, y));
  }

  private scheduleGasClear() {
    if (this.gasClearTimer) {
      clearTimeout(this.gasClearTimer);
    }
    // clear gas 0.6 s after last batch
    this.gasClearTimer = window.setTimeout(() => {
      for (const [mapId, prevList] of this.gasPrevCoords.entries()) {
        const map = this.maps[mapId];
        if (!map || prevList.length === 0) continue;

        for (let i = 0; i < prevList.length; i++) {
          const { x, y } = parseCoordKey(prevList[i]);
          // Zero previous cell, but don't create new tiles just to write 0s.
          this.setGasValue(map, x, y, 0.0, /*createIfMissing*/ false);
        }
      }
    }, 600);
  }

  // Public API called by network handler, one cell at a time.
  // Note: coordinates are now *absolute* world coords, may be negative.
  public handleGas(_: number, mapId: number, x: number, y: number, v: number) {
    // Ensure map exists
    this.maps[mapId] || this.createMap(mapId);

    // No toroidal wrap: world is sparse and unbounded.
    const key = makeCoordKey(x, y);

    let stage = this.gasStaging.get(mapId);
    if (!stage) {
      stage = new Map<CoordKey, number>();
      this.gasStaging.set(mapId, stage);
    }
    stage.set(key, v);

    // Debounced flush at end of tick: treats one Packet as one "batch"
    if (this.gasFlushHandle === undefined) {
      this.gasFlushHandle = window.setTimeout(() => {
        this.gasFlushHandle = undefined;
        this.flushGasBatches();
      }, 0);
    }
  }
  public isOpaque(mapId: number, x: number, y: number): boolean {
    // You can tune this to your glyphs. For now: typical wall chars.
    try {
      const chip = this.getChipId(mapId, x, y);
      const ch = chip.char;
      // Adjust to your tileset: add/remove characters as needed.
      return ch === "#" || ch === "+" || ch === "|" || ch === "-" || ch === "X";
    } catch {
      // Outside known tiles: treat as blocking vision.
      return true;
    }
  }
  // Cull previous batch and apply the newly staged batch for all maps.
  private flushGasBatches(): void {
    // Cull old
    for (const [mapId, prevList] of this.gasPrevCoords.entries()) {
      const map = this.maps[mapId];
      if (!map || prevList.length === 0) continue;

      for (let i = 0; i < prevList.length; i++) {
        const { x, y } = parseCoordKey(prevList[i]);
        this.setGasValue(map, x, y, 0.0, /*createIfMissing*/ false);
      }
    }

    // Write new & record coords for the next cull
    for (const [mapId, stage] of this.gasStaging.entries()) {
      const map = this.maps[mapId] || this.createMap(mapId);
      const nextPrev: CoordKey[] = [];

      for (const [coordKey, val] of stage.entries()) {
        const { x, y } = parseCoordKey(coordKey);
        this.setGasValue(map, x, y, val, /*createIfMissing*/ true);
        nextPrev.push(coordKey);
      }

      this.gasPrevCoords.set(mapId, nextPrev);
      stage.clear();
    }

    // Remove emptied staging maps to keep memory tidy
    this.gasStaging.clear();
    this.scheduleGasClear();
  }

  // Helper: write a single gas cell, routing into the appropriate 16x16 tile.
  // x,y are absolute world coordinates (can be negative).
  private setGasValue(
    map: MapData,
    x: number,
    y: number,
    value: number,
    createIfMissing: boolean
  ): void {
    // For negative coordinates, use Math.floor to pick the correct tile.
    const tileTop = Math.floor(y / CHUNK_HEIGHT) * CHUNK_HEIGHT;
    const tileLeft = Math.floor(x / CHUNK_WIDTH) * CHUNK_WIDTH;
    const key = makeTileKey(tileTop, tileLeft);

    let tile = map.gas.get(key);
    if (!tile) {
      if (!createIfMissing) return;
      tile = new Float32Array(CHUNK_WIDTH * CHUNK_HEIGHT);
      map.gas.set(key, tile);
    }

    const localY = y - tileTop;
    const localX = x - tileLeft;
    const idx = localY * CHUNK_WIDTH + localX;
    tile[idx] = value;
  }

  // ==========================================================================

  private maps: { [mapId: number]: MapData } = {};
  private chips: { [mapId: number]: ChipSet } = {};

  public createMap(mapId: number): MapData {
    const data = new Map<TileKey, Uint8Array>();
    const gas = new Map<TileKey, Float32Array>();

    this.maps[mapId] = {
      id: mapId,
      data,
      gas,
    };
    // Start with empty prev coords so first batch doesn't try to cull
    this.gasPrevCoords.set(mapId, []);
    return this.maps[mapId];
  }

  public hasMap(mapId: number): boolean {
    return mapId in this.maps;
  }

  public getMap(mapId: number): MapData {
    const map = this.maps[mapId];
    if (!map) {
      throw new Error(
        `Attempted to access map #${mapId}, but it has not been initialized by the server.`
      );
    }
    return map;
  }

  public getChipId(mapId: number, globalX: number, globalY: number): ChipData {
    const map = this.getMap(mapId);

    // No toroidal wrap anymore; coords may be negative or arbitrarily large.
    const x = globalX;
    const y = globalY;

    const tileTop = Math.floor(y / CHUNK_HEIGHT) * CHUNK_HEIGHT;
    const tileLeft = Math.floor(x / CHUNK_WIDTH) * CHUNK_WIDTH;
    const key = makeTileKey(tileTop, tileLeft);
    const tile = map.data.get(key);

    if (!tile) {
      throw new Error(
        `Fatal: Tile at [top=${tileTop}, left=${tileLeft}] on map #${mapId} is undefined (chip lookup for global [${globalX}, ${globalY}]).`
      );
    }

    const localY = y - tileTop;
    const localX = x - tileLeft;
    const idx = localY * CHUNK_WIDTH + localX;
    const chipId = tile[idx];

    if (chipId === undefined) {
      throw new Error(
        `Fatal: Chip at [${globalX}, ${globalY}] on map #${mapId} is undefined.`
      );
    }
    return this.getChip(mapId, chipId);
  }

  public getChip(mapId: number, chipId: number): ChipData {
    const chipDeck = this.chips[mapId];
    const chip = chipDeck?.[chipId];

    if (!chip) {
      throw new Error(
        `Fatal: No chip data for ID "${chipId}" on map #${mapId}.`
      );
    }
    return chip;
  }

  public handleChip(chip: Chip): void {
    console.log(
      `[World] Handling Chip: mapId=${chip.mapId}, chipId=${
        chip.id
      }, glyph='${String.fromCharCode(chip.glyph)}'`
    );
    const { mapId, id } = chip;
    if (!this.chips[mapId]) {
      this.chips[mapId] = {};
    }
    this.chips[mapId][id] = {
      char: String.fromCharCode(chip.glyph),
      color: { h: chip.h, s: chip.s, v: chip.v },
    };
  }

  public handleTile(
    mapId: number,
    top: number,
    left: number,
    tileData: Uint8Array
  ): void {
    console.log(
      `[World] Handling Tile: mapId=${mapId} at (${left}, ${top}) with ${tileData.length} bytes.`
    );
    const map = this.maps[mapId] || this.createMap(mapId);

    if (tileData.length !== CHUNK_WIDTH * CHUNK_HEIGHT) {
      throw new Error(
        `[World] Expected tileData length ${CHUNK_WIDTH * CHUNK_HEIGHT}, got ${
          tileData.length
        }.`
      );
    }

    // (top,left) are absolute world coords, can be negative, must be multiple of 16.
    const key = makeTileKey(top, left);
    // Copy so we don't rely on caller buffer.
    map.data.set(key, new Uint8Array(tileData));
  }

  // Optional: helper if you want gas reads symmetrical with getChipId.
  public getGasAt(mapId: number, x: number, y: number): number {
    const map = this.getMap(mapId);
    const tileTop = Math.floor(y / CHUNK_HEIGHT) * CHUNK_HEIGHT;
    const tileLeft = Math.floor(x / CHUNK_WIDTH) * CHUNK_WIDTH;
    const key = makeTileKey(tileTop, tileLeft);
    const tile = map.gas.get(key);
    if (!tile) return 0.0;

    const localY = y - tileTop;
    const localX = x - tileLeft;
    const idx = localY * CHUNK_WIDTH + localX;
    return tile[idx] ?? 0.0;
  }
}

export const world = new World();
