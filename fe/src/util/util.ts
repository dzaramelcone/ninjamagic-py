export function parseDuration(cssValue: string): number {
  const val = cssValue.trim();
  if (val.endsWith("ms")) {
    return parseFloat(val) / 1000;
  }
  return parseFloat(val) || 0;
}

export function cardinalFromDelta(dx: number, dy: number): string {
  if (dx === 0 && dy === 0) return "here";

  // Screen coords are (x right, y down). For math coords, y should increase upward,
  // so we negate dy. atan2 returns angle in [-π, π], 0 along +X (east).
  const angle = Math.atan2(-dy, dx);
  const tau = Math.PI * 2;

  let octant = Math.round((8 * angle) / tau); // range roughly [-4..4]
  if (octant < 0) octant += 8; // wrap to [0..7]

  switch (octant) {
    case 0:
      return "east";
    case 1:
      return "northeast";
    case 2:
      return "north";
    case 3:
      return "northwest";
    case 4:
      return "west";
    case 5:
      return "southwest";
    case 6:
      return "south";
    case 7:
      return "southeast";
    default:
      return "there";
  }
}
