// src/ui/map.ts
import { useGameStore, type EntityPosition } from "../state";
import { world } from "../svc/world";
import { hsv2rgb, lerpHSV_rgb } from "../util/colors";
import { Terminal } from "@xterm/xterm";
import { WebglAddon } from "@xterm/addon-webgl";
import { computeFOV } from "../util/fov";
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

  const FOV_RADIUS = Math.max(COLS, ROWS); // tweak if you want shorter LOS

  // Compute what's currently visible
  const visible = computeFOV(player.x, player.y, FOV_RADIUS, (x, y) =>
    world.isOpaque(player.map_id, x, y)
  );

  // Mark all visible tiles as "seen" in memory
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

      // For visible & seen tiles we still want to use the actual chip.
      let char = " ";
      let color = { h: 0, s: 0, v: 1 };

      try {
        const chip = world.getChipId(player.map_id, worldX, worldY);
        char = chip.char;
        color = chip.color;
      } catch {
        // If something went missing, we just keep it blank.
      }

      const hasEntity = isEntityAt(player.map_id, worldX, worldY);
      const glyph = hasEntity ? "@" : char;

      if (isVisible) {
        // 2) Currently visible: full brightness + gas
        const [fr, fg, fb] = hsv2rgb(color.h, color.s, color.v);
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
        // Dim by reducing saturation + value in HSV.
        const dimS = color.s * 0.85;
        const dimV = color.v * 0.44;
        const [fr, fg, fb] = hsv2rgb(color.h, dimS, dimV);

        // Slightly dark background to distinguish from void
        const [br, bg, bb] = BASE_BG;
        out += `\x1b[48;2;${br};${bg};${bb}m\x1b[38;2;${fr};${fg};${fb}m${glyph}`;
      }
    }
    if (vy < ROWS - 1) out += "\r\n";
  }

  out += "\u001B[?25l\x1b[0m";
  term.write(out);
}
