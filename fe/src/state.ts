//src/state.ts
import { createStore } from "zustand/vanilla";
import { ROWS, COLS } from "./ui/map";
const PLAYER_ID = 0;

export type EntityPosition = {
  id: number;
  map_id: number;
  x: number;
  y: number;
};

type GameStore = {
  entities: Record<number, EntityPosition>;
  messages: string[];

  getPlayer: () => EntityPosition;
  setPosition: (id: number, map_id: number, x: number, y: number) => void;
  entityChecker: () => (map_id: number, x: number, y: number) => boolean;
  cullPositions: () => void;
};

export const useGameStore = createStore<GameStore>((set, get) => ({
  entities: {},
  messages: [],
  getPlayer: () => {
    return get().entities[PLAYER_ID];
  },
  setPosition: (id, map_id, x, y) => {
    console.log(`Set position id=${id} map_id=${map_id} x=${x} y=${y}`);
    get().entities[id] = { id, map_id, x, y };
  },
  entityChecker: () => {
    const { entities } = get();
    const presenceByMap = new Map<number, Set<string>>();

    for (const id in entities) {
      const entity = entities[id];
      if (!presenceByMap.has(entity.map_id)) {
        presenceByMap.set(entity.map_id, new Set());
      }
      presenceByMap.get(entity.map_id)!.add(`${entity.x},${entity.y}`);
    }
    return (map_id: number, x: number, y: number): boolean => {
      const positionSet = presenceByMap.get(map_id);
      if (!positionSet) return false;
      return positionSet.has(`${x},${y}`);
    };
  },
  cullPositions: () => {
    console.log(`Cull positions`);
    const { entities: entities } = get();
    const player = entities[PLAYER_ID];
    set({
      entities: Object.fromEntries(
        Object.entries(entities).filter(([_, entity]) => {
          return (
            entity.id === PLAYER_ID ||
            (entity.map_id === player.map_id &&
              Math.abs(entity.x - player.x) <= Math.floor(ROWS / 2) &&
              Math.abs(entity.y - player.y) <= Math.floor(COLS / 2))
          );
        })
      ),
    });
  },
}));
