// src/services/network.ts
import { useGameStore } from "../state";
import { world } from "./world";
import { postLine } from "../ui/chat";
import {
  Packet,
  Msg,
  Pos,
  Chip,
  Tile,
  Gas,
  Glyph,
  Noun,
  Health,
  Stance,
} from "../gen/messages";
import { COLS, ROWS } from "../ui/map";

const PLAYER_ID = 0;
const { setPosition, cullPositions, setGlyph, setNoun, setHealth, setStance } =
  useGameStore.getState();

function cardinalFromDelta(dx: number, dy: number): string | null {
  if (dx === 0 && dy === 0) return null;

  const sx = Math.sign(dx);
  const sy = Math.sign(dy);

  // pure vertical
  if (sx === 0) {
    return sy < 0 ? "north" : "south";
  }

  // pure horizontal
  if (sy === 0) {
    return sx > 0 ? "east" : "west";
  }

  // diagonals
  if (sy < 0 && sx > 0) return "northeast";
  if (sy < 0 && sx < 0) return "northwest";
  if (sy > 0 && sx > 0) return "southeast";
  if (sy > 0 && sx < 0) return "southwest";

  return null;
}

function isInView(
  mapId: number,
  x: number,
  y: number,
  player: { map_id: number; x: number; y: number }
): boolean {
  if (mapId !== player.map_id) return false;
  const halfCols = Math.floor(COLS / 2);
  const halfRows = Math.floor(ROWS / 2);
  return (
    Math.abs(x - player.x) <= halfCols && Math.abs(y - player.y) <= halfRows
  );
}

function describeEntityName(id: number): string {
  const { entityMeta } = useGameStore.getState() as any;
  const noun: string | undefined = entityMeta?.[id]?.noun;
  return noun ?? "someone";
}

function formatNameList(names: string[]): string {
  if (names.length === 0) return "";
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  const head = names.slice(0, -1).join(", ");
  const last = names[names.length - 1];
  return `${head} and ${last}`;
}

let ws: WebSocket;
const handlerMap = {
  msg: (body: Msg) => {
    postLine(body.text);
  },
  pos: (body: Pos) => {
    const state = useGameStore.getState() as any;
    const entities = state.entities as Record<
      number,
      { id: number; map_id: number; x: number; y: number }
    >;
    const player = entities[PLAYER_ID];
    const prev = entities[body.id];

    const name = describeEntityName(body.id);

    // ============================================================
    // 1. PLAYER MOVEMENT  — handle “You see X here.”
    // ============================================================
    if (body.id === PLAYER_ID) {
      const hadPrev = !!prev;
      setPosition(body.id, body.mapId, body.x, body.y);

      if (!hadPrev) return; // first spawn, no narration

      const after = useGameStore.getState().entities;

      // collect all entities at player’s new tile
      const hereNames: string[] = [];
      for (const e of Object.values(after)) {
        if (e.id === PLAYER_ID) continue;
        if (e.map_id === body.mapId && e.x === body.x && e.y === body.y) {
          hereNames.push(describeEntityName(e.id));
        }
      }

      if (hereNames.length > 0) {
        const list = formatNameList(hereNames);
        postLine(`You see ${list} here.`);
      }

      return;
    }

    // ============================================================
    // 2. NPC MOVEMENT  — handle ambient movement messages
    // ============================================================
    if (!player) {
      setPosition(body.id, body.mapId, body.x, body.y);
      return;
    }

    const prevAtPlayer =
      prev &&
      prev.map_id === player.map_id &&
      prev.x === player.x &&
      prev.y === player.y;

    const newAtPlayer =
      body.mapId === player.map_id &&
      body.x === player.x &&
      body.y === player.y;

    const prevInView = prev
      ? isInView(prev.map_id, prev.x, prev.y, player)
      : false;
    const newInView = isInView(body.mapId, body.x, body.y, player);

    const moveDir = prev
      ? cardinalFromDelta(body.x - prev.x, body.y - prev.y)
      : null;

    const fromPrevRelToPlayer = prev
      ? cardinalFromDelta(prev.x - player.x, prev.y - player.y)
      : null;
    const fromNewRelToPlayer = cardinalFromDelta(
      body.x - player.x,
      body.y - player.y
    );

    // 1) Entity was on your tile and moved away: "Dzara steps west."
    if (prev && prevAtPlayer && !newAtPlayer && moveDir) {
      postLine(`${name} steps ${moveDir}.`);
    }
    // 2) Entity moved into your tile: "Dzara steps beside you from the east."
    else if (prev && !prevAtPlayer && newAtPlayer) {
      if (fromPrevRelToPlayer) {
        postLine(`${name} steps beside you from the ${fromPrevRelToPlayer}.`);
      } else {
        postLine(`${name} steps beside you here.`);
      }
    }
    // 3) Entity moves out of view: "Dzara leaves west."
    else if (prev && prevInView && !newInView && moveDir) {
      postLine(`${name} leaves ${moveDir}.`);
    }
    // 4) Entity moves into view (was offscreen before): "Dzara arrives from the north."
    else if (prev && !prevInView && newInView) {
      if (fromNewRelToPlayer) {
        postLine(`${name} arrives from the ${fromNewRelToPlayer}.`);
      } else {
        postLine(`${name} arrives.`);
      }
    }
    // 5) First time we ever see this entity ...
    else if (!prev && newInView) {
      if (newAtPlayer) {
        postLine(`You see ${name} here.`);
      } else if (fromNewRelToPlayer) {
        postLine(`You see ${name} to the ${fromNewRelToPlayer}.`);
      } else {
        postLine(`You see ${name} nearby.`);
      }
    }
    setPosition(body.id, body.mapId, body.x, body.y);
  },
  chip: (body: Chip) => {
    world.handleChip(body);
  },
  tile: (body: Tile) => {
    world.handleTile(body.mapId, body.top, body.left, body.data);
  },
  gas: (body: Gas) => {
    world.handleGas(body.id, body.mapId, body.x, body.y, body.v);
  },

  glyph: (body: Glyph) => {
    setGlyph(body.id, body.glyph);
  },
  noun: (body: Noun) => {
    setNoun(body.id, body.text);
  },

  health: (body: Health) => {
    setHealth(body.id, body.pct);
  },

  stance: (body: Stance) => {
    setStance(body.id, body.text);
  },
};

export function initializeNetwork() {
  const url = new URL("/ws", location.origin);
  url.protocol = url.protocol.replace("http", "ws");

  ws = new WebSocket(url);
  ws.binaryType = "arraybuffer";

  ws.addEventListener("message", (ev: MessageEvent<ArrayBuffer>) => {
    const packet = Packet.fromBinary(new Uint8Array(ev.data));
    let posDirty = false;
    for (const kind of packet.envelope) {
      const { body } = kind;

      switch (body.oneofKind) {
        case "msg":
          handlerMap.msg(body.msg);
          break;
        case "chip":
          handlerMap.chip(body.chip);
          break;
        case "tile":
          handlerMap.tile(body.tile);
          break;
        case "gas":
          handlerMap.gas(body.gas);
          break;
        case "glyph":
          handlerMap.glyph(body.glyph);
          break;
        case "noun":
          handlerMap.noun(body.noun);
          break;
        case "health":
          handlerMap.health(body.health);
          break;
        case "stance":
          handlerMap.stance(body.stance);
          break;
      }
    }
    for (const kind of packet.envelope) {
      const { body } = kind;

      switch (body.oneofKind) {
        case "pos":
          handlerMap.pos(body.pos);
          posDirty = true;
          break;
        default:
          // everything else already handled above
          break;
      }
    }
    if (posDirty) {
      cullPositions();
    }
  });
}

export function send(message: string) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(message);
  }
}
