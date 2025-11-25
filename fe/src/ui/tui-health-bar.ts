import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import gsap from "gsap";
import { sharedStyles } from "./tui-styles";
import { parseDuration } from "../util/util";

const BAR_WIDTH = 22;

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function makeBar(fraction: number): string {
  const t = clamp01(fraction);
  const filled = Math.round(t * BAR_WIDTH);
  if (filled <= 0) return " ".repeat(BAR_WIDTH);
  return "█".repeat(filled).padEnd(BAR_WIDTH, " ");
}

@customElement("tui-health-bar")
export class TuiHealthBar extends LitElement {
  @property({ type: Number }) value = 0; // 0..1

  // front = colored, ghost = white behind
  private _frontState = { v: 0 };
  private _ghostState = { v: 0 };

  @state() private _frontText = " ".repeat(BAR_WIDTH);
  @state() private _ghostText = " ".repeat(BAR_WIDTH);
  @state() private _ghostIdle = true; // when true, ghost is fully hidden

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        width: ${BAR_WIDTH}ch;
        font: 300 16px "IBM Plex Mono", monospace;
      }

      .line {
        position: relative;
        white-space: pre;
      }

      .ghost,
      .front {
        position: absolute;
        left: 0;
        top: 0;
      }

      .ghost {
        color: rgba(255, 255, 255, 0.7);
        pointer-events: none;
        opacity: 0;
      }

      .ghost.active {
        opacity: 1;
      }

      .front {
        color: var(--health, #f55);
      }
    `,
  ];

  protected firstUpdated() {
    const t = clamp01(this.value);
    this._frontState.v = t;
    this._ghostState.v = t;
    this._updateTexts();
    this._ghostIdle = true;
  }

  protected updated(changed: PropertyValues) {
    if (!changed.has("value")) return;

    const oldVal = (changed.get("value") as number | undefined) ?? 0;
    const prev = clamp01(oldVal);
    const next = clamp01(this.value);

    gsap.killTweensOf(this._frontState);
    gsap.killTweensOf(this._ghostState);

    const style = getComputedStyle(this);
    const durStr = style.getPropertyValue("--tui-health-duration") || "0.6s";
    const easeStr =
      style.getPropertyValue("--tui-health-ease").trim() || "expo.out";

    const duration = parseDuration(durStr.trim());

    if (!duration || duration <= 0 || prev === next) {
      this._frontState.v = next;
      this._ghostState.v = next;
      this._updateTexts();
      this._ghostIdle = true;
      return;
    }

    if (next > prev) {
      // Increase:
      // - ghost jumps to new value
      // - front animates from prev -> next
      this._ghostState.v = next;
      this._updateTexts();
      this._ghostIdle = false;

      gsap.to(this._frontState, {
        v: next,
        duration,
        ease: easeStr,
        onUpdate: () => this._updateTexts(),
        onComplete: () => {
          this._updateTexts();
          this._ghostIdle = true;
        },
      });
    } else {
      // Decrease:
      // - front jumps to new value
      // - ghost animates from prev -> next
      this._frontState.v = next;
      this._updateTexts();
      this._ghostIdle = false;

      gsap.to(this._ghostState, {
        v: next,
        duration,
        ease: easeStr,
        onUpdate: () => this._updateTexts(),
        onComplete: () => {
          this._updateTexts();
          this._ghostIdle = true;
        },
      });
    }
  }

  private _updateTexts() {
    this._frontText = makeBar(this._frontState.v);
    this._ghostText = makeBar(this._ghostState.v);
  }

  render() {
    // prettier-ignore
    return html`<div class="line"><span class="ghost ${this._ghostIdle ? "" : "active"}">${this._ghostText}</span><span class="front">${this._frontText}</span> </div>`;
  }
}
