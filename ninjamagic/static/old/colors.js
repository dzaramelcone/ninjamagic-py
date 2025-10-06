const pack = (r, g, b) => (r << 16) | (g << 8) | b;

const unpack = (rgb) => [(rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255];

const hex2int = (hex) => pack(...hex2rgb(hex));

function int2hex(rgbInt) {
  const [r, g, b] = unpack(rgbInt);
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

const hex2rgb = (hex) => hex.match(/\w\w/g).map((h) => parseInt(h, 16));

function rgb2hsv(r, g, b) {
  // r-g-b 0-255 → h 0-1, s/v 0-1
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

function hsv2rgb(h, s, v) {
  // h 0-1, s/v 0-1 → r-g-b 0-255
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);
  let r, g, b;
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
  return [(r * 255) | 0, (g * 255) | 0, (b * 255) | 0];
}

function lerpHSV(aRgb, bRgb, t) {
  const [ar, ag, ab] = unpack(aRgb);
  const [br, bg, bb] = unpack(bRgb);
  let [h1, s1, v1] = rgb2hsv(ar, ag, ab);
  let [h2, s2, v2] = rgb2hsv(br, bg, bb);

  /* wrap hue through shortest arc */
  let dh = h2 - h1;
  if (dh > 0.5) dh -= 1;
  if (dh < -0.5) dh += 1;
  const h = (h1 + dh * t + 1) % 1;
  const s = s1 + (s2 - s1) * t;
  const v = v1 + (v2 - v1) * t;

  const [r, g, b] = hsv2rgb(h, s, v);
  return pack(r, g, b);
}

function lerpHSV_rgb(a, b, t) {
  const [h1, s1, v1] = rgb2hsv(a[0], a[1], a[2]);
  const [h2, s2, v2] = rgb2hsv(b[0], b[1], b[2]);
  let dh = h2 - h1;
  if (dh > 0.5) dh -= 1;
  if (dh < -0.5) dh += 1;
  const h = (h1 + dh * t + 1) % 1;
  const s = s1 + (s2 - s1) * t;
  const v = v1 + (v2 - v1) * t;
  return hsv2rgb(h, s, v); // returns [r,g,b]
}

const keyframes = [
  {
    t: 0.0,
    pal: {
      bg: "#1B1E26",
      surface: "#1C1F27",
      primary: "#7DD3FC",
      onSurface: "#ECE6F0",
    },
  }, // true midnight
  {
    t: 0.5,
    pal: {
      bg: "#2A2E37",
      surface: "#333745",
      primary: "#7DD3FC",
      onSurface: "#ECE6F0",
    },
  }, // your “dimly-lit” look
  {
    t: 1.0,
    pal: {
      bg: "#1B1E26",
      surface: "#1C1F27",
      primary: "#7DD3FC",
      onSurface: "#ECE6F0",
    },
  }, // back to midnight
];

function paletteAt(t) {
  for (let i = 1; i < keyframes.length; i++) {
    if (t <= keyframes[i].t) {
      const a = keyframes[i - 1],
        b = keyframes[i];
      const span = (t - a.t) / (b.t - a.t);
      const hex2int = (hex) => pack(...hex2rgb(hex));
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
}
