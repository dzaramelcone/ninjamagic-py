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
  player: EntityPosition,
  isEntityAt: (map_id: number, x: number, y: number) => boolean
) {
  if (!player) return;
  if (!world.hasMap(player.map_id)) return;
  const camLeft = player.x - Math.floor(COLS / 2);
  const camTop = player.y - Math.floor(ROWS / 2);
  let out = "\x1b[H"; // ANSI: Move cursor to home

  for (let vy = 0; vy < ROWS; vy++) {
    const worldY = camTop + vy;
    for (let vx = 0; vx < COLS; vx++) {
      const worldX = camLeft + vx;
      const { char, color } = world.getChipId(player.map_id, worldX, worldY);
      const glyph = isEntityAt(player.map_id, worldX, worldY) ? "@" : char;

      const baseRgb = hsv2rgb(color.h, color.s, color.v);
      const [r, g, b] = lerpHSV_rgb(baseRgb, [28, 31, 39], 0);
      out += `\x1b[38;2;${r};${g};${b}m${glyph}`;
    }
    if (vy < ROWS - 1) out += "\r\n";
  }
  term.write(out + "\u001B[?25l\x1b[0m");
}
