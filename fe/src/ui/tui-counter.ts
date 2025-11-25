//src/ui/tui-counter.ts
import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import gsap from "gsap";
import { sharedStyles } from "./tui-styles";

@customElement("tui-counter")
export class TuiCounter extends LitElement {
  @property({ type: Number }) count = 0;
  @property({ type: String }) label = "Lv";
  @query("span.value") _span!: HTMLElement;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: inline-block;
      }
      .value {
        color: var(--c-mid);
        display: inline-block;
        min-width: 4ch;
        text-align: right;
      }
      .label {
        color: var(--c-low);
      }
    `,
  ];

  protected updated(changedProps: PropertyValues) {
    if (
      changedProps.has("count") &&
      this.count > (changedProps.get("count") as number)
    ) {
      this._animateLevelUp();
    }
  }

  private _animateLevelUp() {
    gsap.killTweensOf(this._span);

    gsap.fromTo(
      this._span,
      {
        color: "#ffffff",
        textShadow: "0 0 8px #ffffff, 0 0 12px #ffffff",
      },
      {
        color: "var(--c-mid)",
        textShadow: "none",
        duration: 2,
        ease: "power2.out",
      }
    );
  }

  render() {
    // prettier-ignore
    return html`<span class="label">${this.label}</span><span class="value">${this.count}</span>`;
  }
}
