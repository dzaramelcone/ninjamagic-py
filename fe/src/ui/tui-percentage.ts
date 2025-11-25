import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import gsap from "gsap";
import { sharedStyles } from "./tui-styles";
import { parseDuration } from "../util/util";

@customElement("tui-percentage")
export class TuiPercentage extends LitElement {
  @property({ type: Number }) value = 0; // 0.0 to 1.0
  @query("span.num") _numSpan!: HTMLElement;

  private _displayObj = { val: 0 };

  static styles = [
    sharedStyles,
    css`
      :host {
        display: inline-block;
        text-align: right;
        width: 5ch;

        /* Defaults */
        --tui-duration: 2s;
        --tui-ease: expo.out;
        /* 'auto', 'increase' (snap to 0 on drop), 'decrease' (snap to 100 on rise) */
        --tui-monotonic: auto;
      }
      .num {
        color: var(--c-mid);
      }
      .unit {
        color: var(--c-low);
      }
    `,
  ];

  protected firstUpdated() {
    this._displayObj.val = this.value * 100;
    if (this._numSpan) {
      this._numSpan.innerText = Math.floor(this._displayObj.val).toString();
    }
  }

  protected updated(changedProps: PropertyValues) {
    if (changedProps.has("value")) {
      const oldVal = changedProps.get("value") as number;
      const target = this.value * 100;

      // Read Styles
      const style = getComputedStyle(this);
      const duration = parseDuration(
        style.getPropertyValue("--tui-duration") || "2s"
      );
      const ease = style.getPropertyValue("--tui-ease").trim() || "expo.out";
      const monotonic = style.getPropertyValue("--tui-monotonic").trim();

      // Handle Monotonic Snapping
      if (monotonic === "increase" && this.value < oldVal) {
        // Value dropped, but we only want to show increases -> snap to 0 first (restart)
        this._displayObj.val = 0;
      } else if (monotonic === "decrease" && this.value > oldVal) {
        // Value rose, but we only want to show decreases -> snap to 100 first (refill)
        this._displayObj.val = 100;
      }

      gsap.to(this._displayObj, {
        val: target,
        duration: duration,
        ease: ease,
        onUpdate: () => {
          if (this._numSpan) {
            this._numSpan.innerText = Math.floor(
              this._displayObj.val
            ).toString();
          }
        },
        onStart: () => {
          // Flash if jumping significantly (checking actual data delta)
          if (target - oldVal * 100 > 5) {
            gsap.fromTo(
              this._numSpan,
              { color: "#ffffff" }, // Explicit white for guaranteed brightness
              { color: "var(--c-mid)", duration: 0.4 }
            );
          }
        },
      });
    }
  }

  render() {
    return html`<span class="num">0</span><span class="unit">%</span>`;
  }
}
