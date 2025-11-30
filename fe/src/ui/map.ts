// src/ui/map.ts
import { useGameStore, type EntityPosition, type EntityMeta } from "../state";
import { world } from "../svc/world";
import { hsv2rgb, lerpHSV_rgb } from "../util/colors";
import { Terminal } from "@xterm/xterm";
import { WebglAddon } from "@xterm/addon-webgl";
import { computeFOV } from "../util/fov";
import "@xterm/xterm/css/xterm.css";

export const COLS = 13;
export const ROWS = 13;

export type EntityLookupFn = (
  map_id: number,
  x: number,
  y: number
) => { position: EntityPosition; meta?: EntityMeta } | undefined;

export type TileSample = {
  glyph: string;
  color: { h: number; s: number; v: number };
};

/**
 * Returns the glyph + HSV color for a given world tile,
 * combining base chip color and entity overrides.
 */
export function getTile(
  map_id: number,
  worldX: number,
  worldY: number,
  entityLookup: EntityLookupFn
): TileSample {
  let char = " ";
  let tileColor = { h: 0, s: 0, v: 1 };

  try {
    const chip = world.getChipId(map_id, worldX, worldY);
    char = chip.char;
    tileColor = chip.color;
  } catch {
    // keep defaults
  }

  const entity = entityLookup(map_id, worldX, worldY);

  let glyph = char;
  let glyphColor = tileColor;

  if (entity?.meta?.glyph) {
    glyph = entity.meta.glyph;
    const { h = tileColor.h, s = tileColor.s, v = tileColor.v } = entity.meta;
    glyphColor = { h, s, v };
  }

  return { glyph, color: glyphColor };
}

export function initMap(element: HTMLElement) {
  const term = new Terminal({
    rows: ROWS,
    cols: COLS,
    scrollback: 0,
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 32,
    letterSpacing: 20,
    cursorBlink: false,
    allowTransparency: true,
    theme: { background: "#00000000" },
  });

  term.loadAddon(new WebglAddon());
  term.open(element);

  function tick() {
    const { getPlayer, entityLookup } = useGameStore.getState();
    const player = getPlayer();
    const lookupFn = entityLookup();

    composeFrame(term, player, lookupFn);
    requestAnimationFrame(tick);
  }

  tick();
}

function composeFrame(
  term: Terminal,
  player: EntityPosition | undefined,
  entityLookup: EntityLookupFn
) {
  if (!player) return;
  if (!world.hasMap(player.map_id)) return;

  const FOV_RADIUS = Math.max(COLS, ROWS);

  const visible = computeFOV(player.x, player.y, FOV_RADIUS, (x, y) =>
    world.isOpaque(player.map_id, x, y)
  );

  for (const key of visible) {
    const [xs, ys] = key.split(",");
    const x = Number(xs);
    const y = Number(ys);
    world.markSeen(player.map_id, x, y);
  }

  const camLeft = player.x - Math.floor(COLS / 2);
  const camTop = player.y - Math.floor(ROWS / 2);

  const BASE_BG: [number, number, number] = [28, 31, 39];
  const GAS_PURPLE: [number, number, number] = [160, 0, 255];

  let out = "\x1b[H"; // Move cursor home

  for (let vy = 0; vy < ROWS; vy++) {
    const worldY = camTop + vy;
    for (let vx = 0; vx < COLS; vx++) {
      const worldX = camLeft + vx;
      const key = `${worldX},${worldY}`;
      const isVisible = visible.has(key);
      const wasSeen = world.wasSeen(player.map_id, worldX, worldY);

      // 1) Never seen: hard black void
      if (!isVisible && !wasSeen) {
        out += `\x1b[49m\x1b[38;2;0;0;0m `;
        continue;
      }

      const { glyph, color: glyphColor } = getTile(
        player.map_id,
        worldX,
        worldY,
        entityLookup
      );

      if (isVisible) {
        // 2) Currently visible: full brightness + gas
        const [fr, fg, fb] = hsv2rgb(glyphColor.h, glyphColor.s, glyphColor.v);
        const gasV = world.getGasAt(player.map_id, worldX, worldY);

        if (gasV > 0) {
          const t = Math.min(1, Math.max(0, gasV));
          const eased = Math.sqrt(1 - (t - 1) * (t - 1));
          const [br, bg, bb] = lerpHSV_rgb(BASE_BG, GAS_PURPLE, eased);
          out += `\x1b[48;2;${br};${bg};${bb}m\x1b[38;2;${fr};${fg};${fb}m${glyph}`;
        } else {
          out += `\x1b[49m\x1b[38;2;${fr};${fg};${fb}m${glyph}`;
        }
      } else {
        // 3) Seen before but not currently visible: dimmer, no gas
        const dimS = glyphColor.s * 0.85;
        const dimV = glyphColor.v * 0.44;
        const [fr, fg, fb] = hsv2rgb(glyphColor.h, dimS, dimV);

        const [br, bg, bb] = BASE_BG;
        out += `\x1b[48;2;${br};${bg};${bb}m\x1b[38;2;${fr};${fg};${fb}m${glyph}`;
      }
    }
    if (vy < ROWS - 1) out += "\r\n";
  }

  out += "\u001B[?25l\x1b[0m";
  term.write(out);
}
