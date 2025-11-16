// src/util/fov.ts

export type IsBlockingFn = (x: number, y: number) => boolean;
type Fraction = { n: number; d: number };

/**
 * Symmetric shadowcasting FOV (Albert Ford) with radius.
 * Returns a Set of "x,y" visible coordinates.
 */
export function computeFOV(
  ox: number,
  oy: number,
  radius: number,
  isBlocking: IsBlockingFn
): Set<string> {
  const visible = new Set<string>();
  visible.add(key(ox, oy)); // origin always visible

  const radiusSq = radius * radius;

  function markVisible(x: number, y: number) {
    const dx = x - ox;
    const dy = y - oy;
    if (dx * dx + dy * dy <= radiusSq) {
      visible.add(key(x, y));
    }
  }

  // ---- Fractions ----------------------------------------------------------

  function frac(n: number, d: number): Fraction {
    return { n, d };
  }

  function roundTiesUp(depth: number, slope: Fraction): number {
    const v = (depth * slope.n) / slope.d;
    return Math.floor(v + 0.5);
  }

  function roundTiesDown(depth: number, slope: Fraction): number {
    const v = (depth * slope.n) / slope.d;
    return Math.ceil(v - 0.5);
  }

  function colGteDepthSlope(col: number, depth: number, s: Fraction): boolean {
    // col >= depth * (n/d)  <=>  col * d >= depth * n
    return col * s.d >= depth * s.n;
  }

  function colLteDepthSlope(col: number, depth: number, s: Fraction): boolean {
    // col <= depth * (n/d)  <=>  col * d <= depth * n
    return col * s.d <= depth * s.n;
  }

  function slope(tile: [number, number]): Fraction {
    const [row, col] = tile;
    // (2*col - 1) / (2*row)
    return frac(2 * col - 1, 2 * row);
  }

  // ---- Quadrant -----------------------------------------------------------

  const NORTH = 0;
  const EAST = 1;
  const SOUTH = 2;
  const WEST = 3;

  class Quadrant {
    cardinal: number;
    ox: number;
    oy: number;

    constructor(cardinal: number, originX: number, originY: number) {
      this.cardinal = cardinal;
      this.ox = originX;
      this.oy = originY;
    }

    transform(tile: [number, number]): { x: number; y: number } {
      const [row, col] = tile;
      switch (this.cardinal) {
        case NORTH:
          return { x: this.ox + col, y: this.oy - row };
        case SOUTH:
          return { x: this.ox + col, y: this.oy + row };
        case EAST:
          return { x: this.ox + row, y: this.oy + col };
        case WEST:
          return { x: this.ox - row, y: this.oy + col };
        default:
          return { x: this.ox, y: this.oy };
      }
    }
  }

  // ---- Row ----------------------------------------------------------------

  class Row {
    depth: number;
    startSlope: Fraction;
    endSlope: Fraction;

    constructor(depth: number, startSlope: Fraction, endSlope: Fraction) {
      this.depth = depth;
      this.startSlope = startSlope;
      this.endSlope = endSlope;
    }

    tiles(): [number, number][] {
      const minCol = roundTiesUp(this.depth, this.startSlope);
      const maxCol = roundTiesDown(this.depth, this.endSlope);
      const result: [number, number][] = [];
      for (let col = minCol; col <= maxCol; col++) {
        result.push([this.depth, col]);
      }
      return result;
    }

    next(): Row {
      return new Row(this.depth + 1, this.startSlope, this.endSlope);
    }
  }

  // ---- Core scan ----------------------------------------------------------

  function runQuadrant(cardinal: number) {
    const q = new Quadrant(cardinal, ox, oy);
    const firstRow = new Row(1, frac(-1, 1), frac(1, 1));

    function scan(row: Row): void {
      if (row.depth > radius) return;

      let prevTile: [number, number] | null = null;

      for (const tile of row.tiles()) {
        const { x, y } = q.transform(tile);
        const tileIsWall = isBlocking(x, y);
        const [, col] = tile;

        const tileSym =
          colGteDepthSlope(col, row.depth, row.startSlope) &&
          colLteDepthSlope(col, row.depth, row.endSlope);

        if (tileIsWall || tileSym) {
          markVisible(x, y);
        }

        if (prevTile) {
          const prev = q.transform(prevTile);
          const prevIsWall = isBlocking(prev.x, prev.y);

          if (prevIsWall && !tileIsWall) {
            // left edge of wall -> tighten startSlope
            row.startSlope = slope(tile);
          }

          if (!prevIsWall && tileIsWall) {
            // entering wall -> spawn child row
            const nextRow = row.next();
            nextRow.endSlope = slope(tile);
            scan(nextRow);
          }
        }

        prevTile = tile;
      }

      if (prevTile) {
        const last = q.transform(prevTile);
        if (!isBlocking(last.x, last.y)) {
          scan(row.next());
        }
      }
    }

    scan(firstRow);
  }

  runQuadrant(NORTH);
  runQuadrant(SOUTH);
  runQuadrant(EAST);
  runQuadrant(WEST);

  return visible;
}

// ---- Util -----------------------------------------------------------------

function key(x: number, y: number): string {
  return `${x},${y}`;
}
