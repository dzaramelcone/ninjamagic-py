import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import gsap from "gsap";
import { sharedStyles } from "./tui-styles";
import { parseDuration } from "../util/util";

@customElement("tui-micro-bar")
export class TuiMicroBar extends LitElement {
  @property({ type: Number }) value = 0; // 0.0 to 1.0

  @query(".fill") _fill!: HTMLElement;
  @query(".empty") _empty!: HTMLElement;
  @query(".gap") _gap!: HTMLElement;
  static styles = [
    sharedStyles,
    css`
      :host {
        display: inline-block;
        vertical-align: middle;
        /* Defaults */
        --tui-duration: 2s;
        --tui-ease: expo.out;
        --tui-monotonic: auto;

        width: var(--tui-micro-bar-width, 10ch);
        height: 1em;
        margin-left: 1ch;
      }
      .track {
        width: 100%;
        height: 100%;
        position: relative;
        overflow: hidden;
        transform: scaleY(0.2);
        border-radius: 4px;

        display: flex;
        flex-direction: row;
        align-items: stretch;
      }

      .bar {
        height: 100%;
        flex-basis: 0;
      }

      .fill {
        background-color: var(--c-mid);
        flex-grow: 0;
        min-width: 0.2em;
        border-radius: 3px;
        /* Prepare for box-shadow bloom */
        box-shadow: none;
      }

      .empty {
        background-color: var(--c-low);
        flex-grow: 1;
        border-radius: 3px;
      }

      .gap {
        width: 0.575ch;
        height: 100%;
        background-color: var(--c-bg);
        flex-shrink: 0;
      }
    `,
  ];

  private _getGapWidth(val: number): string {
    const MAX_GAP = 0.575;
    const dist = Math.min(val, 1.0 - val);
    const factor = Math.min(1, dist * 25);
    return `${MAX_GAP * factor}ch`;
  }

  protected updated(changedProps: PropertyValues) {
    if (changedProps.has("value")) {
      const oldVal = changedProps.get("value") as number;

      const style = getComputedStyle(this);
      const duration = parseDuration(
        style.getPropertyValue("--tui-duration") || "2s"
      );
      const ease = style.getPropertyValue("--tui-ease").trim() || "expo.out";
      const monotonic = style.getPropertyValue("--tui-monotonic").trim();

      let snapToZero = false;
      let snapToFull = false;
      const targetGap = this._getGapWidth(this.value);

      if (monotonic === "increase" && this.value < oldVal) snapToZero = true;
      else if (monotonic === "decrease" && this.value > oldVal)
        snapToFull = true;
      else if (monotonic === "auto" && oldVal > this.value) snapToZero = true;
      // Helper for the flash tween to avoid duplication
      const triggerFlash = () => {
        gsap.fromTo(
          this._fill,
          {
            backgroundColor: "#ffffff",
            boxShadow: "0 0 8px #ffffff",
          },
          {
            backgroundColor: "var(--c-mid)",
            boxShadow: "none",
            duration: 0.5,
            ease: "power2.out",
          }
        );
      };
      if (snapToZero) {
        // 1. Physics: Snap to 0, then grow to target
        gsap.fromTo(
          this._fill,
          { flexGrow: 0 },
          { flexGrow: this.value, duration, ease }
        );
        gsap.fromTo(
          this._empty,
          { flexGrow: 1 },
          { flexGrow: 1.0 - this.value, duration, ease }
        );
        // Gap logic: At 0 fill, gap is physically 0. Snap to 0, grow to target.
        gsap.fromTo(
          this._gap,
          { width: "0ch" },
          { width: targetGap, duration, ease }
        );

        // 2. Flash
        triggerFlash();
      } else if (snapToFull) {
        // 1. Physics: Snap to 1, then shrink to target
        gsap.fromTo(
          this._fill,
          { flexGrow: 1 },
          { flexGrow: this.value, duration, ease }
        );
        gsap.fromTo(
          this._empty,
          { flexGrow: 0 },
          { flexGrow: 1.0 - this.value, duration, ease }
        );
        // Gap logic: At full fill, gap is physically 0. Snap to 0, grow to target.
        gsap.fromTo(
          this._gap,
          { width: "0ch" },
          { width: targetGap, duration, ease }
        );

        // 2. Flash
        triggerFlash();
      } else {
        // Standard Interpolation
        gsap.to(this._fill, {
          flexGrow: this.value,
          duration,
          ease,
          onStart: () => {
            if (this.value - oldVal > 0.05) {
              triggerFlash();
            }
          },
        });
        gsap.to(this._empty, { flexGrow: 1.0 - this.value, duration, ease });
        // Interpolate gap width
        gsap.to(this._gap, { width: targetGap, duration, ease });
      }
    }
  }

  render() {
    return html`
      <div class="track">
        <div class="bar fill"></div>
        <div class="gap"></div>
        <div class="bar empty"></div>
      </div>
    `;
  }
}
