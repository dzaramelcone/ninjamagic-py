export type RGB = [r: number, g: number, b: number];
export type HSV = [h: number, s: number, v: number];
export type PackedRGB = number;
export type HexColor = string;

interface Palette {
  bg: HexColor;
  surface: HexColor;
  primary: HexColor;
  onSurface: HexColor;
}

interface Keyframe {
  t: number;
  pal: Palette;
}

export const pack = (r: number, g: number, b: number): PackedRGB =>
  (r << 16) | (g << 8) | b;

export const unpack = (rgb: PackedRGB): RGB => [
  (rgb >> 16) & 255,
  (rgb >> 8) & 255,
  rgb & 255,
];

export const hex2rgb = (hex: HexColor): RGB => {
  const parts = hex.match(/\w\w/g) || [];
  return parts.map((h) => parseInt(h, 16)) as RGB;
};

export const hex2int = (hex: HexColor): PackedRGB => pack(...hex2rgb(hex));

export function int2hex(rgbInt: PackedRGB): HexColor {
  const [r, g, b] = unpack(rgbInt);
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

export function rgb2hsv(r: number, g: number, b: number): HSV {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b);
  const d = max - min;
  const v = max;
  const s = max === 0 ? 0 : d / max;
  let h = 0;

  if (d !== 0) {
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h /= 6;
  }
  return [h, s, v];
}

export function hsv2rgb(h: number, s: number, v: number): RGB {
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);
  let r = 0,
    g = 0,
    b = 0;

  switch (i % 6) {
    case 0:
      r = v;
      g = t;
      b = p;
      break;
    case 1:
      r = q;
      g = v;
      b = p;
      break;
    case 2:
      r = p;
      g = v;
      b = t;
      break;
    case 3:
      r = p;
      g = q;
      b = v;
      break;
    case 4:
      r = t;
      g = p;
      b = v;
      break;
    case 5:
      r = v;
      g = p;
      b = q;
      break;
  }
  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

export function lerpHSV(
  aRgb: PackedRGB,
  bRgb: PackedRGB,
  t: number
): PackedRGB {
  const [ar, ag, ab] = unpack(aRgb);
  const [br, bg, bb] = unpack(bRgb);
  const [h1, s1, v1] = rgb2hsv(ar, ag, ab);
  const [h2, s2, v2] = rgb2hsv(br, bg, bb);

  let dh = h2 - h1;
  if (dh > 0.5) dh -= 1;
  if (dh < -0.5) dh += 1;
  const h = (h1 + dh * t + 1) % 1;
  const s = s1 + (s2 - s1) * t;
  const v = v1 + (v2 - v1) * t;

  const [r, g, b] = hsv2rgb(h, s, v);
  return pack(r, g, b);
}

export function lerpHSV_rgb(a: RGB, b: RGB, t: number): RGB {
  const [h1, s1, v1] = rgb2hsv(a[0], a[1], a[2]);
  const [h2, s2, v2] = rgb2hsv(b[0], b[1], b[2]);

  let dh = h2 - h1;
  if (dh > 0.5) dh -= 1;
  if (dh < -0.5) dh += 1;
  const h = (h1 + dh * t + 1) % 1;
  const s = s1 + (s2 - s1) * t;
  const v = v1 + (v2 - v1) * t;

  return hsv2rgb(h, s, v);
}

export const keyframes: Keyframe[] = [
  {
    t: 0.0,
    pal: {
      bg: "#1B1E26",
      surface: "#1C1F27",
      primary: "#7DD3FC",
      onSurface: "#ECE6F0",
    },
  },
  {
    t: 0.5,
    pal: {
      bg: "#2A2E37",
      surface: "#333745",
      primary: "#7DD3FC",
      onSurface: "#ECE6F0",
    },
  },
  {
    t: 1.0,
    pal: {
      bg: "#1B1E26",
      surface: "#1C1F27",
      primary: "#7DD3FC",
      onSurface: "#ECE6F0",
    },
  },
];

export function paletteAt(t: number): { [key: string]: PackedRGB } {
  for (let i = 1; i < keyframes.length; i++) {
    if (t <= keyframes[i].t) {
      const a = keyframes[i - 1];
      const b = keyframes[i];
      const span = (t - a.t) / (b.t - a.t);
      return {
        bg: lerpHSV(hex2int(a.pal.bg), hex2int(b.pal.bg), span),
        surface: lerpHSV(hex2int(a.pal.surface), hex2int(b.pal.surface), span),
        primary: lerpHSV(hex2int(a.pal.primary), hex2int(b.pal.primary), span),
        onSurface: lerpHSV(
          hex2int(a.pal.onSurface),
          hex2int(b.pal.onSurface),
          span
        ),
      };
    }
  }

  // Return the last keyframe's palette if t is out of bounds
  const lastPal = keyframes[keyframes.length - 1].pal;
  return {
    bg: hex2int(lastPal.bg),
    surface: hex2int(lastPal.surface),
    primary: hex2int(lastPal.primary),
    onSurface: hex2int(lastPal.onSurface),
  };
}
