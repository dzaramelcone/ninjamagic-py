import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { sharedStyles } from "./tui-styles";

const BAR_WIDTH = 22;

function makeStanceLine(text: string): string {
  const innerWidth = BAR_WIDTH;
  let content = text;
  if (content.length > innerWidth) {
    content = content.slice(0, innerWidth);
  }
  const spaceTotal = innerWidth - content.length;
  const leftPad = Math.floor(spaceTotal / 2);
  const rightPad = spaceTotal - leftPad;
  return " ".repeat(leftPad) + content + " ".repeat(rightPad);
}

@customElement("tui-label-line")
export class TuiLabelLine extends LitElement {
  @property({ type: String }) text = "";

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        width: ${BAR_WIDTH}ch;
        font: 300 19px "IBM Plex Mono", monospace;
      }

      .line {
        white-space: pre;
        color: var(--c-mid, #aaa);
      }
    `,
  ];

  render() {
    const t = this.text || "";
    const line = makeStanceLine(t);
    return html`<div class="line">${line}</div>`;
  }
}
