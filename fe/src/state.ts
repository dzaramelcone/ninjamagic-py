// src/state.ts
import { createStore } from "zustand/vanilla";
import { ROWS, COLS } from "./ui/map";
const PLAYER_ID = 0;

export type EntityPosition = {
  id: number;
  map_id: number;
  x: number;
  y: number;
};

export type EntityMeta = {
  glyph?: string;
  h?: number;
  s?: number;
  v?: number;
  noun?: string;
  stance?: string;
  condition?: string;
  healthPct?: number; // from Health.pct (0..1)
  stressPct?: number;
};

export type SkillState = {
  name: string;
  rank: number;
  tnl: number;
};

type ServerTimeState = {
  unixSeconds: number | null; // server "now" at last sync
  syncedAtMs: number | null; // performance.now() at last sync
};

type GameStore = {
  entities: Record<number, EntityPosition>;
  entityMeta: Record<number, EntityMeta>;
  messages: string[];
  skills: SkillState[];
  serverTime: ServerTimeState;

  getPlayer: () => EntityPosition;
  setPosition: (id: number, map_id: number, x: number, y: number) => void;

  // existing
  entityChecker: () => (map_id: number, x: number, y: number) => boolean;

  // NEW: for getting the actual entity + meta at a tile
  entityLookup: () => (
    map_id: number,
    x: number,
    y: number
  ) => { position: EntityPosition; meta?: EntityMeta } | undefined;

  cullPositions: () => void;
  setGlyph: (
    id: number,
    glyph: string,
    h: number,
    s: number,
    v: number
  ) => void;
  setNoun: (id: number, text: string) => void;
  setHealth: (id: number, pct: number, stressPct: number) => void;
  setStance: (id: number, text: string) => void;
  setCondition: (id: number, text: string) => void;
  setSkill: (name: string, rank: number, tnl: number) => void;
  setServerTime: (unixSeconds: bigint) => void;
  getServerNow: () => Date;
};

export const useGameStore = createStore<GameStore>((set, get) => ({
  entities: {},
  entityMeta: {},
  messages: [],
  skills: [],
  serverTime: {
    unixSeconds: null,
    syncedAtMs: null,
  },

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
  entityLookup: () => {
    const { entities, entityMeta } = get();
    // map_id -> "x,y" -> entity id
    const presenceByMap = new Map<number, Map<string, number>>();

    for (const [idStr, entity] of Object.entries(entities)) {
      const id = Number(idStr);
      let byCoord = presenceByMap.get(entity.map_id);
      if (!byCoord) {
        byCoord = new Map<string, number>();
        presenceByMap.set(entity.map_id, byCoord);
      }

      const key = `${entity.x},${entity.y}`;
      const existing = byCoord.get(key);

      if (existing === PLAYER_ID) {
        // Player already there → keep player
        continue;
      }

      if (id === PLAYER_ID) {
        // Current entity is player → override
        byCoord.set(key, id);
        continue;
      }

      // Otherwise: last entity wins
      byCoord.set(key, id);
    }

    return (
      map_id: number,
      x: number,
      y: number
    ): { position: EntityPosition; meta?: EntityMeta } | undefined => {
      const coordMap = presenceByMap.get(map_id);
      if (!coordMap) return undefined;

      const id = coordMap.get(`${x},${y}`);
      if (id === undefined) return undefined;

      const position = entities[id];
      if (!position) return undefined;

      const meta = entityMeta[id];
      return { position, meta };
    };
  },
  cullPositions: () => {
    console.log(`Cull positions`);
    const { entities, entityMeta } = get();
    const player = entities[PLAYER_ID];
    if (!player) {
      return;
    }

    const keptEntries = Object.entries(entities).filter(([_, entity]) => {
      const e = entity as EntityPosition;
      return (
        e.id === PLAYER_ID ||
        (e.map_id === player.map_id &&
          Math.abs(e.x - player.x) <= Math.floor(ROWS / 2) &&
          Math.abs(e.y - player.y) <= Math.floor(COLS / 2))
      );
    });

    const newEntities: Record<number, EntityPosition> = Object.fromEntries(
      keptEntries
    ) as Record<number, EntityPosition>;

    const keptIds = new Set<number>(
      Object.keys(newEntities).map((k) => Number(k))
    );

    const newMeta: Record<number, EntityMeta> = Object.fromEntries(
      Object.entries(entityMeta).filter(([id]) => keptIds.has(Number(id)))
    ) as Record<number, EntityMeta>;

    set({
      entities: newEntities,
      entityMeta: newMeta,
    });
  },

  setGlyph: (id, glyph, h, s, v) =>
    set((state) => ({
      entityMeta: {
        ...state.entityMeta,
        [id]: {
          ...(state.entityMeta[id] ?? {}),
          glyph,
          h,
          s,
          v,
        },
      },
    })),

  setNoun: (id, text) =>
    set((state) => ({
      entityMeta: {
        ...state.entityMeta,
        [id]: {
          ...(state.entityMeta[id] ?? {}),
          noun: text,
        },
      },
    })),

  setHealth: (id, pct, stressPct) =>
    set((state) => ({
      entityMeta: {
        ...state.entityMeta,
        [id]: {
          ...(state.entityMeta[id] ?? {}),
          healthPct: pct,
          stressPct: stressPct,
        },
      },
    })),

  setStance: (id, text) =>
    set((state) => ({
      entityMeta: {
        ...state.entityMeta,
        [id]: {
          ...(state.entityMeta[id] ?? {}),
          stance: text,
        },
      },
    })),

  setCondition: (id, text) =>
    set((state) => ({
      entityMeta: {
        ...state.entityMeta,
        [id]: {
          ...(state.entityMeta[id] ?? {}),
          condition: text,
        },
      },
    })),

  setSkill: (name, rank, tnl) =>
    set((state) => {
      const existingIdx = state.skills.findIndex((s) => s.name === name);

      if (existingIdx !== -1) {
        const newSkills = [...state.skills];
        newSkills[existingIdx] = { name, rank, tnl };
        return { skills: newSkills };
      } else {
        return { skills: [...state.skills, { name, rank, tnl }] };
      }
    }),

  setServerTime: (unixSeconds: bigint) =>
    set(() => ({
      serverTime: {
        unixSeconds: Number(unixSeconds),
        syncedAtMs: performance.now(),
      },
    })),

  getServerNow: () => {
    const { serverTime } = get();
    if (!serverTime.unixSeconds || !serverTime.syncedAtMs) {
      return new Date();
    }
    const elapsedMs = performance.now() - serverTime.syncedAtMs;
    const ms = serverTime.unixSeconds * 1000 + elapsedMs;
    return new Date(ms);
  },
}));
