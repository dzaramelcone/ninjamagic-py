// src/ui/nearby.ts
import { useGameStore, type EntityPosition } from "../state";

const PLAYER_ID = 0;
const BAR_WIDTH = 22;

type EntityMeta = {
  glyph?: string;
  noun?: string;
  stance?: string;
  healthPct?: number;
};

type FullEntity = EntityPosition & EntityMeta;

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function makeHealthBar(pct: number | undefined): string | null {
  if (pct === undefined) return null;
  const t = clamp01(pct);
  const filled = Math.round(t * BAR_WIDTH);
  if (filled <= 0) return " ".repeat(BAR_WIDTH);
  return "█".repeat(filled).padEnd(BAR_WIDTH, " ");
}

function directionLabel(player: EntityPosition, ent: EntityPosition): string {
  const dx = ent.x - player.x;
  const dy = ent.y - player.y;

  if (dx === 0 && dy === 0) return "(here)";

  const vert = dy < 0 ? "north" : dy > 0 ? "south" : "";
  const horiz = dx < 0 ? "west" : dx > 0 ? "east" : "";

  if (vert && horiz) return `(${vert}${horiz})`;
  if (vert) return `(${vert})`;
  if (horiz) return `(${horiz})`;
  return "";
}

/**
 * Build the name/dir line, exactly BAR_WIDTH chars:
 * - "glyph: noun" on the left
 * - direction label right-aligned (last char at BAR_WIDTH-1)
 * - at least one space between name and direction when there is a direction
 */
function makeNameLine(player: EntityPosition, ent: FullEntity): string {
  const isPlayer = ent.id === PLAYER_ID;
  const glyph = ent.glyph ?? "@";
  const noun = isPlayer ? "you" : ent.noun ?? "unknown";
  const namePart = `${glyph}: ${noun}`;
  const dir = isPlayer ? "(here)" : directionLabel(player, ent);

  // No direction: just left-align name and pad to BAR_WIDTH.
  if (!dir) {
    const truncated = namePart.slice(0, BAR_WIDTH);
    return truncated.padEnd(BAR_WIDTH, " ");
  }

  // With direction: right-align direction, ensure last char of dir is last char of line.
  const dlen = dir.length;
  if (dlen >= BAR_WIDTH) {
    // Pathological: direction too long, just take the rightmost BAR_WIDTH chars.
    return dir.slice(dlen - BAR_WIDTH);
  }

  // Leave at least 1 space before dir if possible.
  const maxNameWidth = BAR_WIDTH - dlen - 1;
  const truncatedName = namePart.slice(0, maxNameWidth);
  const left = truncatedName.padEnd(maxNameWidth, " ");
  return left + " " + dir; // length == BAR_WIDTH
}

/**
 * Build stance line:
 * - '[' at col 0
 * - ']' at col BAR_WIDTH-1
 * - stance text centered in between
 */
function makeStanceLine(stance: string): string {
  const innerWidth = BAR_WIDTH - 2;
  let content = stance;
  if (content.length > innerWidth) {
    content = content.slice(0, innerWidth);
  }
  const spaceTotal = innerWidth - content.length;
  const leftPad = Math.floor(spaceTotal / 2);
  const rightPad = spaceTotal - leftPad;
  return "[" + " ".repeat(leftPad) + content + " ".repeat(rightPad) + "]";
}

function formatEntityChunk(player: EntityPosition, ent: FullEntity): string[] {
  const lines: string[] = [];

  // First line: name + dir, fixed width
  lines.push(makeNameLine(player, ent));

  const healthBar = makeHealthBar(ent.healthPct);
  if (healthBar) {
    lines.push(healthBar);
  }

  if (ent.stance) {
    lines.push(makeStanceLine(ent.stance));
  }

  return lines;
}

function buildNearbyText(): string {
  const { entities, entityMeta } = useGameStore.getState();

  const player = entities[PLAYER_ID];
  if (!player) return "";

  // Merge position + meta into a list
  const all: FullEntity[] = Object.values(entities).map((pos) => {
    const meta = entityMeta[pos.id] ?? {};
    return { ...pos, ...meta };
  });

  // Same map only
  const sameMap = all.filter((e) => e.map_id === player.map_id);

  // Player first, others by distance
  const playerList: FullEntity[] = [];
  const others: FullEntity[] = [];
  for (const e of sameMap) {
    if (e.id === PLAYER_ID) playerList.push(e);
    else others.push(e);
  }

  others.sort((a, b) => {
    const da =
      (a.x - player.x) * (a.x - player.x) + (a.y - player.y) * (a.y - player.y);
    const db =
      (b.x - player.x) * (b.x - player.x) + (b.y - player.y) * (b.y - player.y);
    return da - db;
  });

  const ordered = [...playerList, ...others];
  if (ordered.length === 0) return "";

  const lines: string[] = [];
  for (const ent of ordered) {
    const chunk = formatEntityChunk(player, ent);
    for (const line of chunk) {
      lines.push(line);
    }
    lines.push(""); // blank line between entities
  }

  // trim trailing blank
  while (lines.length && lines[lines.length - 1] === "") {
    lines.pop();
  }

  return lines.join("\n");
}

export function initNearby(element: HTMLElement) {
  // Make sure it renders like TUI
  element.style.whiteSpace = "pre";
  element.style.fontFamily = element.style.fontFamily || "monospace";

  function tick() {
    const text = buildNearbyText();
    element.textContent = text;
    requestAnimationFrame(tick);
  }

  tick();
}
