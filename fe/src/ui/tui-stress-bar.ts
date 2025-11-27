import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, queryAll } from "lit/decorators.js";
import gsap from "gsap";
import { sharedStyles } from "./tui-styles";

const CHAR_SOLID = "■";
const CHAR_OUTLINE = "□";
const SEGMENT_COUNT = 10 as const;

type SegmentState = 0 | 1 | 2;

interface Counts {
  outlineCount: number;
  solidCount: number;
}

@customElement("tui-stress-bar")
export class TuiStressBar extends LitElement {
  @property({ type: Number }) value = 0; // 0.0 to 1.0

  @queryAll(".seg") private _segs!: NodeListOf<HTMLElement>;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: inline-block;
        margin-left: 1.5ch;
        min-width: 22ch;
        vertical-align: middle;
        font: 300 19px "IBM Plex Mono", monospace;
        --tui-monotonic: increase;
      }

      .seg {
        overflow: visible;
        display: inline-block;
        padding-right: 1ch;
        transition: none;
      }
      .solid {
        color: var(--c-mid);
      }
      .outline-active {
        color: var(--c-mid);
      }
      .outline-empty {
        display: none;
      }
    `,
  ];

  private getCounts(val: number): Counts {
    // Clamp to [0, 1]
    const v = Math.max(0, Math.min(val, 1));
    const isFull = v >= 0.99;

    let outlineCount = 0;
    if (v >= 0.5) {
      outlineCount = SEGMENT_COUNT;
    } else {
      outlineCount = Math.floor((v / 0.5) * SEGMENT_COUNT);
    }

    let solidCount = 0;
    if (v < 0.5) {
      solidCount = 0;
    } else if (isFull) {
      solidCount = SEGMENT_COUNT;
    } else {
      solidCount = Math.floor(((v - 0.5) / 0.5) * SEGMENT_COUNT);
    }

    return { outlineCount, solidCount };
  }

  private getSegmentState(index: number, counts: Counts): SegmentState {
    if (index < counts.solidCount) return 2;
    if (index < counts.outlineCount) return 1;
    return 0;
  }
  protected updated(changedProps: PropertyValues) {
    if (!changedProps.has("value")) return;

    // Old value might be undefined on the first update
    const oldValRaw = changedProps.get("value") as number | undefined;
    const oldVal = typeof oldValRaw === "number" ? oldValRaw : 0;

    const style = getComputedStyle(this);
    const monotonic = (
      style.getPropertyValue("--tui-monotonic") || "auto"
    ).trim();

    let effectiveOldVal = oldVal;
    if (monotonic === "increase" && this.value < oldVal) {
      // Treat a decrease as if we're starting from 0 again
      effectiveOldVal = 0;
    }

    const currentCounts = this.getCounts(this.value);
    const oldCounts = this.getCounts(effectiveOldVal);

    if (!this._segs || this._segs.length === 0) return;

    this._segs.forEach((seg, i) => {
      const oldState = this.getSegmentState(i, oldCounts);
      const newState = this.getSegmentState(i, currentCounts);

      // Always clear existing tweens before deciding what to do
      gsap.killTweensOf(seg);

      if (newState <= oldState) {
        // If we went backwards or stayed the same, just ensure we don't keep
        // any stale inline glow. Classes already reflect the new state.
        if (newState < oldState) {
          seg.removeAttribute("style");
        }
        return;
      }

      // State increased: flash this segment
      gsap.fromTo(
        seg,
        {
          color: "#ffffff",
          textShadow: "0 0 10px #ffffff, 0 0 20px #ffffff",
        },
        {
          color: "var(--c-mid)",
          textShadow: "none",
          duration: 0.8,
          ease: "power2.out",
        }
      );
    });
  }

  render() {
    const { outlineCount, solidCount } = this.getCounts(this.value);

    const segments = Array.from({ length: SEGMENT_COUNT }, (_, i) => {
      let char = CHAR_OUTLINE;
      let cls = "outline-empty";

      if (i < solidCount) {
        char = CHAR_SOLID;
        cls = "solid";
      } else if (i < outlineCount) {
        char = CHAR_OUTLINE;
        cls = "outline-active";
      }

      return html`<span class="seg ${cls}">${char}</span>`;
    });

    return html`<span class="container">${segments}</span>`;
  }
}
