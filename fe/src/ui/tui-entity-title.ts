// src/ui/tui-entity-title.ts
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { sharedStyles } from "./tui-styles";
import { hsvaToRgba as hsva2Rgba } from "../util/colors";

const BAR_WIDTH = 22;

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
        font: 300 19px "IBM Plex Mono", monospace;
        line-height: 1;
      }

      .line {
        white-space: pre;
      }

      .glyph {
        /* color via inline HSVA */
      }

      .colon {
        color: var(--c-low, #888);
      }

      .name {
        color: var(--c-mid, #ccc);
      }

      .dir {
        color: var(--c-low, #888);
      }
    `,
  ];

  private get _color(): string {
    return hsva2Rgba(this.h, this.s, this.v, this.a);
  }

  render() {
    const labelName = this.name || "unknown";
    const dirText = this.direction || "";

    // Use original alignment logic
    const { left, dir } = clampLabel({
      glyph: this.glyph || "@",
      name: labelName,
      dir: dirText,
    });

    // Split `left` into glyph / colon / name segments
    let glyphText = "";
    let colonText = "";
    let nameText = "";

    const colonIdx = left.indexOf(":");

    if (colonIdx === -1) {
      // No colon in the clamped text (edge case: long dir or extreme truncation)
      if (left.length > 0) {
        glyphText = left.charAt(0);
        nameText = left.slice(1);
      }
    } else {
      glyphText = left.slice(0, colonIdx); // usually just the glyph
      colonText = left.charAt(colonIdx); // the ':' itself
      nameText = left.slice(colonIdx + 1); // everything after ':'
    }

    // prettier-ignore
    return html`<div class="line"><span class="glyph" style=${`color: ${this._color};`}>${glyphText}</span><span class="colon">${colonText}</span><span class="name">${nameText}</span><span class="dir">${dir}</span></div>`;
  }
}
