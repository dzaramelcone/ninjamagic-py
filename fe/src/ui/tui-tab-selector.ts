// src/ui/tui-tab-selector.ts
import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import {
  customElement,
  property,
  query,
  queryAll,
  state,
} from "lit/decorators.js";
import gsap from "gsap";
import { sharedStyles } from "./tui-styles";

@customElement("tui-tab-selector")
export class TuiTabSelector extends LitElement {
  @state() private _labels: string[] = [];

  // Internal index used for animation/layout
  @property({ type: Number }) selectedIndex = 0;

  // Label-based external API
  @property({ type: String }) selectedLabel: string | null = null;

  // "top" (default) or "bottom" for the indicator track position
  @property({ type: String, attribute: "indicator-position", reflect: true })
  indicatorPosition: "top" | "bottom" = "top";

  @query(".track") private _track!: HTMLElement;
  @query(".segment.left") private _leftSeg!: HTMLElement;
  @query(".segment.cursor") private _cursorSeg!: HTMLElement;
  @query(".segment.right") private _rightSeg!: HTMLElement;
  @query(".tabs-row") private _tabsRow!: HTMLElement;
  @query(".content-area") private _contentArea!: HTMLElement;
  @queryAll(".label-text") private _labelEls!: NodeListOf<HTMLElement>;
  @query("slot") private _slot!: HTMLSlotElement;
  @query(".gap-probe") private _gapProbe!: HTMLElement;

  private _gapSize = 0;

  private readonly _onResize = () => {
    this._measureGapSize();
    this._updateBounds();
    this._updateBar(false);
  };

  static styles = [
    sharedStyles,
    css`
      :host {
        width: 100%;
        font: 300 19px IBM Plex Mono, monospace;
        --bar-height: 1ch;
        --tui-gap: 1ch;
      }

      .container {
        position: relative;
        display: flex;
        flex-direction: column;
        width: 100%;
      }

      .tabs-row {
        order: 0;
      }
      .track {
        order: 1;
      }
      .content-area {
        order: 2;
      }
      :host([indicator-position="bottom"]) .content-area {
        order: 0;
        // display: flex;
        // flex-direction: column-reverse;
      }
      :host([indicator-position="bottom"]) .track {
        order: 1;
      }
      :host([indicator-position="bottom"]) .tabs-row {
        order: 2;
      }

      .track {
        position: relative;
        width: 100%;
        height: var(--bar-height);
        margin-bottom: 0.5em;
        border-radius: 4px;
        overflow: hidden;
        background: transparent;
        transform: scaleY(0.2);
        transform-origin: center bottom;
      }

      .segment {
        position: absolute;
        top: 0;
        height: 100%;
        border-radius: 2px;
      }

      .segment.left,
      .segment.right {
        background-color: var(--c-low);
        transition: background-color 0.3s;
      }

      .segment.cursor {
        background-color: var(--c-mid);
        z-index: 2;
      }

      .tabs-row {
        display: flex;
        flex-direction: row;
        width: 100%;
      }

      .tab {
        flex: 1;
        display: flex;
        justify-content: center;
        cursor: pointer;
        opacity: 0.6;
        transition: opacity 0.3s;
        user-select: none;
      }

      .tab:hover,
      .tab.active {
        opacity: 1;
      }

      .label-text {
        transition: color 0.3s;
        color: var(--c-low);
      }

      .tab.active .label-text {
        color: var(--c-mid);
      }

      .content-area {
        position: relative;
        width: 100%;
      }

      .gap-probe {
        position: absolute;
        visibility: hidden;
        pointer-events: none;
        height: 0;
        width: var(--tui-gap);
      }
    `,
  ];

  protected firstUpdated() {
    this._measureGapSize();
    this._updateBounds();
    this._updateBar(false);
    window.addEventListener("resize", this._onResize);
  }

  disconnectedCallback() {
    window.removeEventListener("resize", this._onResize);
    super.disconnectedCallback();
  }

  protected updated(changedProps: PropertyValues) {
    if (changedProps.has("_labels")) {
      this._ensureSelectedLabel();
      this._syncSelectedIndexFromLabel();
      this.updateComplete.then(() => {
        this._updateBounds();
        this._updateBar(false);
        this._updateContentVisibility();
      });
    }

    if (changedProps.has("selectedLabel")) {
      this._syncSelectedIndexFromLabel();
      this._updateBar(true);
      this._updateContentVisibility();
      const index = this.selectedIndex;
      const label = this.selectedLabel;

      this.dispatchEvent(
        new CustomEvent("tui-tab-changed", {
          detail: { index, label },
          bubbles: true,
          composed: true,
        })
      );
    }

    if (changedProps.has("indicatorPosition")) {
      this.updateComplete.then(() => {
        this._updateBounds();
        this._updateBar(false);
      });
    }
  }

  private _measureGapSize() {
    if (this._gapProbe) {
      this._gapSize = this._gapProbe.clientWidth || 0;
    }
  }

  private _handleSlotChange() {
    const elements = this._slot.assignedElements({
      flatten: true,
    }) as HTMLElement[];
    this._labels = elements.map((el) => el.getAttribute("label") || "Untitled");

    this.updateComplete.then(() => {
      this._ensureSelectedLabel();
      this._syncSelectedIndexFromLabel();
      this._updateBounds();
      this._updateBar(false);
      this._updateContentVisibility();
    });
  }

  private _ensureSelectedLabel() {
    if (!this._labels.length) return;

    if (!this.selectedLabel || !this._labels.includes(this.selectedLabel)) {
      const fallback =
        this._labels[this.selectedIndex] ?? this._labels[0] ?? null;
      this.selectedLabel = fallback;
    }
  }

  private _syncSelectedIndexFromLabel() {
    if (!this._labels.length || !this.selectedLabel) return;

    const idx = this._labels.indexOf(this.selectedLabel);
    const clamped = idx >= 0 ? idx : 0;

    if (this.selectedIndex !== clamped) {
      this.selectedIndex = clamped;
    }
  }

  private _updateContentVisibility() {
    const elements = this._slot?.assignedElements({
      flatten: true,
    }) as HTMLElement[];
    if (!elements) return;

    elements.forEach((el, index) => {
      if (index === this.selectedIndex) {
        el.removeAttribute("hidden");
        el.style.display = "";
      } else {
        el.setAttribute("hidden", "");
        el.style.display = "none";
      }
    });
  }

  public selectLabel(label: string) {
    if (!this._labels.length) {
      this.selectedLabel = label;
      return;
    }

    if (!this._labels.includes(label)) return;
    this.selectedLabel = label;
  }

  private _updateBounds() {
    if (!this._contentArea || !this._slot) return;

    const panels = this._slot.assignedElements({
      flatten: true,
    }) as HTMLElement[];
    const labels = this._labelEls;

    let maxPanelHeight = 0;
    let maxPanelWidth = 0;

    if (panels.length) {
      const savedStates = panels.map((el) => ({
        el,
        display: el.style.display,
        hidden: el.hasAttribute("hidden"),
      }));

      panels.forEach((el) => {
        el.style.display = "";
        el.removeAttribute("hidden");
      });

      panels.forEach((el) => {
        const rect = el.getBoundingClientRect();
        maxPanelHeight = Math.max(maxPanelHeight, rect.height);
        maxPanelWidth = Math.max(maxPanelWidth, rect.width);
      });

      savedStates.forEach(({ el, display, hidden }) => {
        el.style.display = display;
        if (hidden) el.setAttribute("hidden", "");
        else el.removeAttribute("hidden");
      });
    }

    let labelsWidth = 0;
    if (labels && labels.length) {
      labels.forEach((el) => {
        const rect = el.getBoundingClientRect();
        labelsWidth += rect.width;
      });
    }

    const maxWidth = Math.max(maxPanelWidth, labelsWidth);

    if (maxWidth > 0) {
      const w = Math.round(maxWidth);
      this._contentArea.style.minWidth = `${w}px`;
      this.style.minWidth = `${w}px`;
    }

    if (maxPanelHeight > 0) {
      const panelH = Math.round(maxPanelHeight);
      this._contentArea.style.height = `${panelH}px`;
      this._contentArea.style.minHeight = `${panelH}px`;
    }
  }

  private _getGapWidth(): number {
    return this._gapSize || 0;
  }

  private _updateBar(animate: boolean = true) {
    if (!this._track || !this._tabsRow) return;

    const label = this._labelEls?.[this.selectedIndex];
    if (!label) return;

    const trackWidth = this._track.clientWidth;
    const tabsRect = this._tabsRow.getBoundingClientRect();
    const labelRect = label.getBoundingClientRect();

    if (!trackWidth || !tabsRect.width || !labelRect.width) return;

    const gapSize = this._getGapWidth();

    const labelLeftInRow = labelRect.left - tabsRect.left;
    const leftRatio = labelLeftInRow / tabsRect.width;
    const widthRatio = labelRect.width / tabsRect.width;

    let cursorLeft = leftRatio * trackWidth;
    let cursorWidth = widthRatio * trackWidth;

    cursorLeft = Math.max(0, Math.min(cursorLeft, trackWidth));
    cursorWidth = Math.max(0, Math.min(cursorWidth, trackWidth - cursorLeft));

    const desiredGap = gapSize;

    const baseCursorLeft = cursorLeft;

    const gapLeftStart = Math.max(0, baseCursorLeft - desiredGap);

    const leftSegLeft = 0;
    const leftSegWidth = Math.max(0, gapLeftStart - leftSegLeft);

    const cursorLeftFinal = baseCursorLeft;

    const cursorWidthFinal = Math.max(
      0,
      Math.min(cursorWidth, trackWidth - cursorLeftFinal)
    );
    const cursorRightFinal = cursorLeftFinal + cursorWidthFinal;

    const gapRightEnd = Math.min(trackWidth, cursorRightFinal + desiredGap);

    const rightSegLeft = gapRightEnd;
    const rightSegWidth = Math.max(0, trackWidth - rightSegLeft);

    const r = (n: number) => Math.round(n);

    const LSegLeft = r(leftSegLeft);
    const LSegWidth = r(leftSegWidth);
    const CLeft = r(cursorLeftFinal);
    const CWidth = r(cursorWidthFinal);
    const RSegLeft = r(rightSegLeft);
    const RSegWidth = r(rightSegWidth);

    const duration = animate ? 0.66 : 0;
    const ease = "expo.out";

    gsap.killTweensOf(this._leftSeg);
    gsap.killTweensOf(this._cursorSeg);
    gsap.killTweensOf(this._rightSeg);

    gsap.to(this._leftSeg, {
      left: LSegLeft,
      width: LSegWidth,
      duration,
      ease,
    });

    gsap.to(this._cursorSeg, {
      left: CLeft,
      width: CWidth,
      duration,
      ease,
    });

    gsap.to(this._rightSeg, {
      left: RSegLeft,
      width: RSegWidth,
      duration,
      ease,
    });
    const moveDuration = animate ? 2.0 : 0;
    gsap.fromTo(
      this._cursorSeg,
      { backgroundColor: "#ffffff", boxShadow: "0 0 12px #ffffff" },
      {
        backgroundColor: "var(--c-mid)",
        boxShadow: "none",
        duration: moveDuration,
        ease: "expo.out",
      }
    );
  }

  render() {
    return html`
      <div class="container">
        <div class="gap-probe" aria-hidden="true"></div>
        <div class="track">
          <div class="segment left"></div>
          <div class="segment cursor"></div>
          <div class="segment right"></div>
        </div>
        <div class="tabs-row">
          ${this._labels.map(
            (label) => html`
              <div
                class="tab ${label === this.selectedLabel ? "active" : ""}"
                @click=${() => this.selectLabel(label)}
              >
                <span class="label-text">${label}</span>
              </div>
            `
          )}
        </div>
        <div class="content-area">
          <slot @slotchange=${this._handleSlotChange}></slot>
        </div>
      </div>
    `;
  }
}
