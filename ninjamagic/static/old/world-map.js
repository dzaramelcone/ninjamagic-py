const MAP_WIDTH = 520;
const MAP_HEIGHT = 520;

class WorldMaps {
  constructor() {
    this.maps = {};
  }

  getMap(mapId) {
    if (!this.maps[mapId]) {
      const data = new Array(MAP_HEIGHT);
      for (let i = 0; i < MAP_HEIGHT; i++) {
        data[i] = new Uint8Array(MAP_WIDTH);
      }
      this.maps[mapId] = {
        id: mapId,
        legend: {},
        data: data,
      };
      console.log(`Initialized new map structure for ID: ${mapId}`);
    }
    return this.maps[mapId];
  }

  handleLegend(payload) {
    const { mapId, l } = payload;
    this.getMap(mapId).legend = l;
    console.log(`Stored legend for map ${mapId}`);
  }

  handleTile(payload) {
    const dataView = new DataView(payload);
    const mapId = dataView.getUint16(0, false);
    const top = dataView.getInt32(2, false);
    const left = dataView.getInt32(6, false);
    const tileData = new Uint8Array(payload, 10);

    const _map = this.getMap(mapId);

    for (let y = 0; y < CHUNK_HEIGHT; y++) {
      const sourceRow = tileData.subarray(
        y * CHUNK_WIDTH,
        (y + 1) * CHUNK_WIDTH
      );
      const destRow = _map.data[top + y];
      destRow.set(sourceRow, left);
    }
  }

  getTileAt(mapId, globalX, globalY) {
    const map = this.maps[mapId];
    if (!map) return undefined;
    const x = ((globalX % map.width) + map.width) % map.width;
    const y = ((globalY % map.height) + map.height) % map.height;
    return map.data[y][x];
  }

  getGlyph(mapId, tileId) {
    const map = this.maps[mapId];
    if (!map || !map.legend) return null;
    return map.legend[tileId] || null;
  }
}
