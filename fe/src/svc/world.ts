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
  width: number;
  height: number;
}

class World {
  private maps: { [mapId: number]: MapData } = {};
  private chips: { [mapId: number]: ChipSet } = {};

  public createMap(mapId: number): MapData {
    const data: Uint8Array[] = new Array(MAP_HEIGHT);
    for (let i = 0; i < MAP_HEIGHT; i++) {
      data[i] = new Uint8Array(MAP_WIDTH);
    }
    this.maps[mapId] = {
      id: mapId,
      data: data,
      width: MAP_WIDTH,
      height: MAP_HEIGHT,
    };
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
    // Get the map for this tile, creating it if it doesn't exist.
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
