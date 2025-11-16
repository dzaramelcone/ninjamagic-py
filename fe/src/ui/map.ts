// src/ui/map.ts
import { useGameStore, type EntityPosition } from "../state";
import { world } from "../svc/world";
import { hsv2rgb, lerpHSV_rgb } from "../util/colors";
import { Terminal } from "@xterm/xterm";
import { WebglAddon } from "@xterm/addon-webgl";
import "@xterm/xterm/css/xterm.css";

export const COLS = 13;
export const ROWS = 13;

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
    const { getPlayer, entityChecker } = useGameStore.getState();
    composeFrame(term, getPlayer(), entityChecker());
    requestAnimationFrame(tick);
  }
  tick();
}

function composeFrame(
  term: Terminal,
  player: EntityPosition | undefined,
  isEntityAt: (map_id: number, x: number, y: number) => boolean
) {
  if (!player) return;
  if (!world.hasMap(player.map_id)) return;

  const map = world.getMap(player.map_id);
  const camLeft = player.x - Math.floor(COLS / 2);
  const camTop = player.y - Math.floor(ROWS / 2);

  // base + gas colors in RGB
  const BASE_BG: [number, number, number] = [28, 31, 39];
  const GAS_PURPLE: [number, number, number] = [160, 0, 255];

  let out = "\x1b[H"; // Move cursor home

  for (let vy = 0; vy < ROWS; vy++) {
    const worldY = camTop + vy;
    for (let vx = 0; vx < COLS; vx++) {
      const worldX = camLeft + vx;

      const { char, color } = world.getChipId(player.map_id, worldX, worldY);
      const glyph = isEntityAt(player.map_id, worldX, worldY) ? "@" : char;

      const [fr, fg, fb] = hsv2rgb(color.h, color.s, color.v);

      // directly read the map gas array using same indices as world coords
      const gasV = map.gas[worldY]?.[worldX] ?? 0; // undefined-safe for edge maps (no wrap here)

      if (gasV > 0) {
        const t = Math.min(1, Math.max(0, gasV));
        const eased = Math.sqrt(1 - (t - 1) * (t - 1));
        const [br, bg, bb] = lerpHSV_rgb(BASE_BG, GAS_PURPLE, eased);
        out += `\x1b[48;2;${br};${bg};${bb}m\x1b[38;2;${fr};${fg};${fb}m${glyph}`;
      } else {
        out += `\x1b[49m\x1b[38;2;${fr};${fg};${fb}m${glyph}`;
      }
    }
    if (vy < ROWS - 1) out += "\r\n";
  }

  out += "\u001B[?25l\x1b[0m";
  term.write(out);
}
