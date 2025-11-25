import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import gsap from "gsap";
import { sharedStyles } from "./tui-styles";

const CHAR_MACRO_FULL = "▰";
const CHAR_MACRO_EMPTY = "▱";

@customElement("tui-macro-bar")
export class TuiMacroBar extends LitElement {
  @property({ type: Number }) value = 0; // 0.0 to 1.0
  @query(".container") _container!: HTMLElement;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: inline-block;
        margin-left: 1ch;
        vertical-align: middle;
        --tui-monotonic: auto;
      }
      .seg {
        overflow: visible;
        display: inline-block;
        transition: none;
      }
      .fill {
        color: var(--c-ember);
      }
      .empty {
        color: var(--c-low);
      }
    `,
  ];

  protected updated(changedProps: PropertyValues) {
    if (changedProps.has("value")) {
      const oldVal = changedProps.get("value") as number;
      const currentBlock = Math.floor(this.value * 10);
      const oldBlock = Math.floor(oldVal * 10);
      const isFull = this.value >= 0.99;

      const segs = this._container.querySelectorAll(".seg");

      // 1. Cleanup Step:
      // Strip inline styles from any segment that shouldn't be filled.
      segs.forEach((seg, i) => {
        const shouldBeFill = i < currentBlock || isFull;
        if (!shouldBeFill) {
          gsap.killTweensOf(seg);
          seg.removeAttribute("style");
        }
      });

      // 2. Determine effective start block for animation
      // Read monotonic setting to decide if we snapped
      const style = getComputedStyle(this);
      const monotonic = style.getPropertyValue("--tui-monotonic").trim();

      let effectiveOldBlock = oldBlock;

      if (monotonic === "increase" && this.value < oldVal) {
        // Value dropped (e.g. level up wrap-around), so we treat animation as starting from 0
        effectiveOldBlock = 0;
      }

      // 3. Animation Step:
      // If we gained blocks (or wrapped around), animate them.
      if (currentBlock > effectiveOldBlock) {
        for (let i = effectiveOldBlock; i < currentBlock; i++) {
          if (i >= 0 && i < segs.length) {
            const el = segs[i];

            // "Satisfying" Flash:
            // Start: Pure White (#ffffff) + Heavy Glow
            // End: Ember Color + No Glow
            gsap.fromTo(
              el,
              {
                color: "#ffffff",
                textShadow: "0 0 10px #ffffff, 0 0 20px #ffffff",
              },
              {
                color: "var(--c-ember)",
                textShadow: "none",
                duration: 0.8,
                ease: "power2.out",
              }
            );
          }
        }
      }
    }
  }

  render() {
    const displayValue = this.value;
    const count = Math.floor(displayValue * 10);
    const isFull = displayValue >= 0.99;

    const templates = [];

    for (let i = 0; i < 10; i++) {
      const isFill = i < count || isFull;
      const char = isFill ? CHAR_MACRO_FULL : CHAR_MACRO_EMPTY;
      const cls = isFill ? "fill" : "empty";
      templates.push(html`<span class="seg ${cls}">${char}</span>`);
    }
    return html`<span class="container">${templates}</span>`;
  }
}
