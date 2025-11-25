import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { sharedStyles } from "./tui-styles";

const BAR_WIDTH = 22;

function hsvaToRgba(h: number, s: number, v: number, a: number): string {
  const C = v * s;
  const Hp = (h % 360) / 60;
  const X = C * (1 - Math.abs((Hp % 2) - 1));
  let r = 0,
    g = 0,
    b = 0;

  if (0 <= Hp && Hp < 1) [r, g, b] = [C, X, 0];
  else if (1 <= Hp && Hp < 2) [r, g, b] = [X, C, 0];
  else if (2 <= Hp && Hp < 3) [r, g, b] = [0, C, X];
  else if (3 <= Hp && Hp < 4) [r, g, b] = [0, X, C];
  else if (4 <= Hp && Hp < 5) [r, g, b] = [X, 0, C];
  else if (5 <= Hp && Hp < 6) [r, g, b] = [C, 0, X];

  const m = v - C;
  const R = Math.round((r + m) * 255);
  const G = Math.round((g + m) * 255);
  const B = Math.round((b + m) * 255);

  return `rgba(${R}, ${G}, ${B}, ${a})`;
}

function clampLabel(parts: { glyph: string; name: string; dir: string }): {
  left: string;
  dir: string;
} {
  const { glyph, name, dir } = parts;
  const namePart = `${glyph}: ${name}`;

  if (!dir) {
    const truncated = namePart.slice(0, BAR_WIDTH);
    const padded = truncated.padEnd(BAR_WIDTH, " ");
    return { left: padded, dir: "" };
  }

  const dlen = dir.length;
  if (dlen >= BAR_WIDTH) {
    const shortDir = dir.slice(dlen - BAR_WIDTH);
    return { left: "", dir: shortDir };
  }

  const maxNameWidth = BAR_WIDTH - dlen - 1; // one space before dir
  const truncatedName = namePart.slice(0, maxNameWidth);
  const left = truncatedName.padEnd(maxNameWidth, " ") + " ";
  return { left, dir };
}

@customElement("tui-entity-title")
export class TuiEntityTitle extends LitElement {
  @property({ type: String }) glyph = "@";
  @property({ type: String }) name = "unknown";
  @property({ type: String }) direction = "";
  @property({ type: Boolean }) isPlayer = false;

  @property({ type: Number }) h = 0;
  @property({ type: Number }) s = 0;
  @property({ type: Number }) v = 1;
  @property({ type: Number }) a = 1;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        width: ${BAR_WIDTH}ch;
        font: 300 16px "IBM Plex Mono", monospace;
        line-height: 1;
      }

      .line {
        white-space: pre;
      }

      .dir {
        color: var(--c-low, #888);
      }
    `,
  ];

  private get _color(): string {
    return hsvaToRgba(this.h, this.s, this.v, this.a);
  }

  render() {
    const labelName = this.isPlayer ? "you" : this.name || "unknown";
    const dirText = this.isPlayer ? "(here)" : this.direction;

    const { left, dir } = clampLabel({
      glyph: this.glyph || "@",
      name: labelName,
      dir: dirText || "",
    });
    // prettier-ignore
    return html`<div class="line"><span style=${`color: ${this._color};`}>${left}</span><span class="dir">${dir}</span></div>`;
  }
}
