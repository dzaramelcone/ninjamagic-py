// src/svc/world.ts
import type { Chip } from "../gen/messages";

const CHUNK_WIDTH = 16;
const CHUNK_HEIGHT = 16;
const MAP_WIDTH = 520;
const MAP_HEIGHT = 520;

interface ChipData {
  char: string;
  color: { h: number; s: number; v: number };
}

type ChipSet = {
  [chipId: string]: ChipData;
};

interface MapData {
  id: number;
  data: Uint8Array[];
  gas: Float32Array[];
  width: number;
  height: number;
}

class World {
  // ==== NEW: gas double-buffer bookkeeping ==================================
  // mapId -> staging (linearIndex -> value)
  private gasStaging: Map<number, Map<number, number>> = new Map();
  // mapId -> list of linear indices written in previous batch (for culling)
  private gasPrevIndices: Map<number, number[]> = new Map();
  // coalesces many handleGas() calls in the same WS packet into one flush
  private gasFlushHandle: number | undefined;
  private gasClearTimer: number | undefined;

  private scheduleGasClear() {
    if (this.gasClearTimer) {
      clearTimeout(this.gasClearTimer);
    }
    // clear gas 0.6 s after last batch
    this.gasClearTimer = window.setTimeout(() => {
      for (const [mapId, prevList] of this.gasPrevIndices.entries()) {
        const map = this.maps[mapId];
        if (!map) continue;
        const width = map.width;
        for (let i = 0; i < prevList.length; i++) {
          const idx = prevList[i];
          const y = (idx / width) | 0;
          const x = idx - y * width;
          map.gas[y][x] = 0;
        }
      }
    }, 600);
  }
  // Public API called by network handler, one row at a time.
  public handleGas(_: number, mapId: number, x: number, y: number, v: number) {
    // Ensure map exists
    const map = this.maps[mapId] || this.createMap(mapId);

    // Toroidal wrap (same style as getChipId)
    const nx = ((x % map.width) + map.width) % map.width;
    const ny = ((y % map.height) + map.height) % map.height;

    // Stage this write
    let stage = this.gasStaging.get(mapId);
    if (!stage) {
      stage = new Map<number, number>();
      this.gasStaging.set(mapId, stage);
    }
    const idx = ny * map.width + nx;

    // If server ever sends v=0.0 we allow it, but normal flow culls old cells
    // so typical batches only contain positive gas values.
    stage.set(idx, v);

    // Debounced flush at end of tick: treats one Packet as one "batch"
    if (this.gasFlushHandle === undefined) {
      this.gasFlushHandle = window.setTimeout(() => {
        this.gasFlushHandle = undefined;
        this.flushGasBatches();
      }, 0);
    }
  }

  // Cull previous batch and apply the newly staged batch for all maps.
  private flushGasBatches(): void {
    // Cull old
    for (const [mapId, prevList] of this.gasPrevIndices.entries()) {
      const map = this.maps[mapId];
      if (!map || prevList.length === 0) continue;

      const width = map.width;
      for (let i = 0; i < prevList.length; i++) {
        const idx = prevList[i];
        const y = (idx / width) | 0;
        const x = idx - y * width;
        // Zero out the previous value (cull)
        map.gas[y][x] = 0.0;
      }
    }

    // Write new & record indices for the next cull
    for (const [mapId, stage] of this.gasStaging.entries()) {
      const map = this.maps[mapId] || this.createMap(mapId);
      const width = map.width;
      const nextPrev: number[] = [];

      // Batch write the staged rows
      for (const [idx, val] of stage.entries()) {
        const y = (idx / width) | 0;
        const x = idx - y * width;
        map.gas[y][x] = val;
        nextPrev.push(idx);
      }

      // Swap the "prev" set for next time and clear staging
      this.gasPrevIndices.set(mapId, nextPrev);
      stage.clear();
    }

    // Remove emptied staging maps to keep memory tidy
    this.gasStaging.clear();
    this.scheduleGasClear();
  }

  // ==========================================================================

  private maps: { [mapId: number]: MapData } = {};
  private chips: { [mapId: number]: ChipSet } = {};

  public createMap(mapId: number): MapData {
    const data: Uint8Array[] = new Array(MAP_HEIGHT);
    const gas: Float32Array[] = new Array(MAP_HEIGHT);
    for (let i = 0; i < MAP_HEIGHT; i++) {
      data[i] = new Uint8Array(MAP_WIDTH);
      gas[i] = new Float32Array(MAP_WIDTH);
    }
    this.maps[mapId] = {
      id: mapId,
      data: data,
      gas: gas,
      width: MAP_WIDTH,
      height: MAP_HEIGHT,
    };
    // Start with empty prev indices so first batch doesn't try to cull
    this.gasPrevIndices.set(mapId, []);
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
    const x = ((globalX % map.width) + map.width) % map.width;
    const y = ((globalY % map.height) + map.height) % map.height;

    const chipId = map.data[y]?.[x];
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

    for (let y = 0; y < CHUNK_HEIGHT; y++) {
      const sourceRow = tileData.subarray(
        y * CHUNK_WIDTH,
        (y + 1) * CHUNK_WIDTH
      );
      const destRow = map.data[top + y];
      if (!destRow) throw new Error("Falsy dest row");
      destRow.set(sourceRow, left);
    }
  }
}

export const world = new World();
