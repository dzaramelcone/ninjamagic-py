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

const { setPosition, cullPositions, setGlyph, setNoun, setHealth, setStance } =
  useGameStore.getState();

let ws: WebSocket;
const handlerMap = {
  msg: (body: Msg) => {
    postLine(body.text);
  },
  pos: (body: Pos) => {
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
        case "pos":
          handlerMap.pos(body.pos);
          posDirty = true;
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
