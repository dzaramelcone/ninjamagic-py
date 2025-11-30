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
  Condition,
  Skill,
  Datetime,
} from "../gen/messages";
import { COLS, ROWS } from "../ui/map";
import { cardinalFromDelta } from "../util/util";

const PLAYER_ID = 0;
const NONE_LEVEL_ID = 1;
type PosLike = { id: number; map_id: number; x: number; y: number };
const {
  setPosition,
  cullPositions,
  setGlyph,
  setNoun,
  setHealth,
  setStance,
  setSkill,
  setCondition,
  setServerTime,
} = useGameStore.getState();

function describeEntityName(id: number): string {
  const { entityMeta } = useGameStore.getState() as any;
  const noun: string | undefined = entityMeta?.[id]?.noun;

  if (!noun || noun.length === 0) return "someone";

  // Proper name → leave as-is
  if (noun[0] === noun[0].toUpperCase()) return noun;

  const lower = noun.toLowerCase();

  // 1. Silent H cases → use “an”
  if (/^(honest|hour|honor|honour|heir)/.test(lower)) {
    return `an ${noun}`;
  }

  // 2. "Yoo-" and "W" sounding vowel words → use “a”
  if (
    /^u[bcfhjkqrstnlgm]/.test(lower) || // unicorn, useful, ukulele, uranium, etc.
    /^eu/.test(lower) || // European, eucalyptus
    /^one/.test(lower) // one, once
  ) {
    return `a ${noun}`;
  }

  // 3. Acronyms that begin with a vowel *sound*
  if (/^[AEFHILMNORSX]\b/.test(noun)) {
    return `an ${noun}`;
  }

  // 4. Default vowel-letter rule
  if (/^[aeiou]/.test(lower)) {
    return `an ${noun}`;
  }

  return `a ${noun}`;
}
function formatNameList(names: string[]): string {
  if (names.length === 0) return "";
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  const head = names.slice(0, -1).join(", ");
  const last = names[names.length - 1];
  return `${head} and ${last}`;
}

function isInViewPos(ent: PosLike, player: PosLike | undefined): boolean {
  if (!player) return false;
  if (ent.map_id !== player.map_id) return false;
  const halfCols = Math.floor(COLS / 2);
  const halfRows = Math.floor(ROWS / 2);
  return (
    Math.abs(ent.x - player.x) <= halfCols &&
    Math.abs(ent.y - player.y) <= halfRows
  );
}

function sameTile(a: PosLike, b: PosLike): boolean {
  return a.map_id === b.map_id && a.x === b.x && a.y === b.y;
}
function handlePos(newPos: Pos) {
  // We need both the 'before' and 'after' states to generate a message.
  const beforeState = useGameStore.getState();
  const beforeEntities = beforeState.entities as Record<
    number,
    { id: number; map_id: number; x: number; y: number }
  >;

  const playerId = PLAYER_ID; // Assuming PLAYER_ID is available in scope
  const prevPos = beforeEntities[newPos.id];
  const playerPrevPos = beforeEntities[playerId];

  const entityName = describeEntityName(newPos.id);
  // mutate:
  setPosition(newPos.id, newPos.map_id, newPos.x, newPos.y);

  if (!playerPrevPos) return;
  const afterState = useGameStore.getState();
  const afterEntities = afterState.entities as Record<
    number,
    { id: number; map_id: number; x: number; y: number }
  >;
  const playerNewPos = afterEntities[playerId];

  if (newPos.id === playerId) {
    if (!prevPos) return;
    const playerActuallyMoved = !sameTile(playerPrevPos, playerNewPos);
    if (!playerActuallyMoved) return;
    const hereNames: string[] = [];
    for (const entity of Object.values(afterEntities)) {
      if (entity.id === playerId) continue;
      if (sameTile(entity, playerNewPos)) {
        hereNames.push(describeEntityName(entity.id));
      }
    }
    if (hereNames.length > 0) {
      const list = formatNameList(hereNames);
      postLine(`You see ${list} here.`);
    }
    return;
  }

  const hadPrevPos = !!prevPos;
  const hereBefore = hadPrevPos && sameTile(prevPos!, playerPrevPos);
  const hereAfter = sameTile(newPos, playerNewPos);
  const viewBefore = hadPrevPos && isInViewPos(prevPos!, playerPrevPos);
  const viewAfter = isInViewPos(newPos, playerNewPos);

  const deltaX = hadPrevPos ? newPos.x - prevPos!.x : 0;
  const deltaY = hadPrevPos ? newPos.y - prevPos!.y : 0;
  const moveDir = hadPrevPos ? cardinalFromDelta(deltaX, deltaY) : null;

  const relPrev =
    hadPrevPos && !hereBefore
      ? cardinalFromDelta(
          prevPos!.x - playerNewPos.x,
          prevPos!.y - playerNewPos.y
        )
      : null;

  const relNext = !hereAfter
    ? cardinalFromDelta(newPos.x - playerNewPos.x, newPos.y - playerNewPos.y)
    : null;

  if (hadPrevPos && hereBefore && !hereAfter && moveDir) {
    if (viewAfter) {
      postLine(`${entityName} steps ${moveDir}.`);
    } else {
      postLine(`${entityName} leaves ${moveDir}.`);
    }
    return;
  }

  if (!hereBefore && hereAfter) {
    if (hadPrevPos && relPrev) {
      postLine(`${entityName} steps beside you from the ${relPrev}.`);
    } else {
      postLine(`${entityName} steps beside you here.`);
    }
    return;
  }

  if (hadPrevPos && viewBefore && !viewAfter && !hereAfter && moveDir) {
    if (newPos.map_id == NONE_LEVEL_ID) {
      postLine(`${entityName} leaves.`);
    } else {
      postLine(`${entityName} leaves ${moveDir}.`);
    }
    return;
  }

  if (hadPrevPos && !viewBefore && viewAfter && !hereAfter) {
    if (relNext) {
      postLine(`${entityName} arrives from the ${relNext}.`);
    } else {
      postLine(`${entityName} arrives.`);
    }
    return;
  }
  if (!hadPrevPos && viewAfter) {
    if (hereAfter) {
      postLine(`You see ${entityName} here.`);
    } else if (relNext) {
      postLine(`You see ${entityName} to the ${relNext}.`);
    } else {
      postLine(`You see ${entityName} nearby.`);
    }
    return;
  }
}
let ws: WebSocket;
const handlerMap = {
  msg: (body: Msg) => {
    postLine(body.text);
  },
  pos: (newPos: Pos) => {
    handlePos(newPos);
  },
  chip: (body: Chip) => {
    world.handleChip(body);
  },
  tile: (body: Tile) => {
    world.handleTile(body.map_id, body.top, body.left, body.data);
  },
  gas: (body: Gas) => {
    world.handleGas(body.id, body.map_id, body.x, body.y, body.v);
  },

  glyph: (body: Glyph) => {
    setGlyph(body.id, body.glyph, body.h, body.s, body.v);
  },
  noun: (body: Noun) => {
    setNoun(body.id, body.text);
  },

  health: (body: Health) => {
    setHealth(body.id, body.pct, body.stress_pct);
  },

  stance: (body: Stance) => {
    setStance(body.id, body.text);
  },

  skill: (body: Skill) => {
    setSkill(body.name, body.rank, body.tnl);
  },

  datetime: (body: Datetime) => {
    setServerTime(body.seconds);
  },
  condition: (body: Condition) => {
    setCondition(body.id, body.text);
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
        case "skill":
          handlerMap.skill(body.skill);
          break;
        case "datetime":
          handlerMap.datetime(body.datetime);
          break;
        case "condition":
          handlerMap.condition(body.condition);
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
