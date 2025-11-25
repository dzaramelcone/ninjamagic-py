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
  @property({ type: Number }) selectedIndex = 0;

  // "top" (default) or "bottom" for the indicator track position
  @property({ type: String, attribute: "indicator-position", reflect: true })
  indicatorPosition: "top" | "bottom" = "top";

  @query(".track") private _track!: HTMLElement;
  @query(".segment.left") private _leftSeg!: HTMLElement;
  @query(".segment.cursor") private _cursorSeg!: HTMLElement;
  @query(".segment.right") private _rightSeg!: HTMLElement;
  @query(".gap.left") private _leftGap!: HTMLElement;
  @query(".gap.right") private _rightGap!: HTMLElement;
  @query(".tabs-row") private _tabsRow!: HTMLElement;
  @query(".content-area") private _contentArea!: HTMLElement;
  @queryAll(".label-text") private _labelEls!: NodeListOf<HTMLElement>;
  @query("slot") private _slot!: HTMLSlotElement;

  private _gapSize = 0;

  private readonly _onResize = () => {
    this._updateBounds();
    this._updateBar(false);
  };

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        width: 100%;
        font-family: monospace;
        --bar-height: 1em;
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
      }
      :host([indicator-position="bottom"]) .track {
        order: 1;
      }
      :host([indicator-position="bottom"]) .tabs-row {
        order: 2;
      }
      .content-area {
        padding-bottom: calc(var(--bar-height) + 1ch);
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

      .gap {
        position: absolute;
        top: 0;
        height: 100%;
        width: var(--tui-gap);
        background-color: var(--c-bg);
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
      }

      .tab.active .label-text {
        color: var(--c-high);
      }

      .content-area {
        position: relative;
        width: 100%;
      }
    `,
  ];

  protected firstUpdated() {
    if (this._leftGap) {
      this._gapSize = this._leftGap.clientWidth || 0;
    }

    this._updateBounds();
    this._updateBar(false);
    window.addEventListener("resize", this._onResize);
  }

  disconnectedCallback() {
    window.removeEventListener("resize", this._onResize);
    super.disconnectedCallback();
  }

  protected updated(changedProps: PropertyValues) {
    if (changedProps.has("selectedIndex")) {
      this._updateBar(true);
      this._updateContentVisibility();
    }

    if (changedProps.has("_labels")) {
      this.updateComplete.then(() => {
        this._updateBounds();
        this._updateBar(false);
        this._updateContentVisibility();
      });
    }

    if (changedProps.has("indicatorPosition")) {
      // Re-clamp bounds when the layout order changes
      this.updateComplete.then(() => {
        this._updateBounds();
        this._updateBar(false);
      });
    }
  }

  private _handleSlotChange() {
    const elements = this._slot.assignedElements({
      flatten: true,
    }) as HTMLElement[];
    this._labels = elements.map((el) => el.getAttribute("label") || "Untitled");

    this.updateComplete.then(() => {
      this._updateBounds();
      this._updateBar(false);
      this._updateContentVisibility();
    });
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

  private _select(index: number) {
    if (index === this.selectedIndex) return;
    this.selectedIndex = index;

    this.dispatchEvent(
      new CustomEvent("select", {
        detail: { index, label: this._labels[index] },
        bubbles: true,
        composed: true,
      })
    );
  }

  /**
   * Clamp:
   *   - content-area minHeight to tallest panel
   *   - host minHeight to tallest panel + track + tabs
   *   - width to max( labels width sum, widest panel )
   */
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

      // Show all panels to measure intrinsic size
      panels.forEach((el) => {
        el.style.display = "";
        el.removeAttribute("hidden");
      });

      panels.forEach((el) => {
        const rect = el.getBoundingClientRect();
        maxPanelHeight = Math.max(maxPanelHeight, rect.height);
        maxPanelWidth = Math.max(maxPanelWidth, rect.width);
      });

      // Restore
      savedStates.forEach(({ el, display, hidden }) => {
        el.style.display = display;
        if (hidden) el.setAttribute("hidden", "");
        else el.removeAttribute("hidden");
      });
    }

    // Sum label widths to get an intrinsic width for the header row
    let labelsWidth = 0;
    if (labels && labels.length) {
      labels.forEach((el) => {
        const rect = el.getBoundingClientRect();
        labelsWidth += rect.width;
      });
    }

    const maxWidth = Math.max(maxPanelWidth, labelsWidth);

    // Clamp widths: widget and content share the same minimum width
    if (maxWidth > 0) {
      const w = Math.round(maxWidth);
      this._contentArea.style.minWidth = `${w}px`;
      this.style.minWidth = `${w}px`;
    }

    // **Hard clamp** content height to tallest panel
    if (maxPanelHeight > 0) {
      const panelH = Math.round(maxPanelHeight);
      this._contentArea.style.height = `${panelH}px`; // <— key change
      this._contentArea.style.minHeight = `${panelH}px`; // optional belt-and-suspenders
    }

    // Note: we no longer set this.style.minHeight.
    // Overall widget height = content fixed height + fixed track height + fixed tabs height.
  }

  private _getGapWidth(): number {
    return this._gapSize || 0;
  }

  /**
   * Update the segmented bar based on the active label.
   * Uses absolute positioning so it cannot affect layout.
   */
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

    // Layout: [leftSeg][leftGap][cursor][rightGap][rightSeg]
    const desiredGap = gapSize;

    let leftGapLeft = cursorLeft - desiredGap;
    if (leftGapLeft < 0) leftGapLeft = 0;
    let leftGapWidth = cursorLeft - leftGapLeft;
    if (leftGapWidth < 0) leftGapWidth = 0;

    const cursorLeftFinal = leftGapLeft + leftGapWidth;
    const cursorRight = cursorLeftFinal + cursorWidth;

    let rightGapLeft = cursorRight;
    let rightGapRight = rightGapLeft + desiredGap;
    if (rightGapRight > trackWidth) rightGapRight = trackWidth;
    let rightGapWidth = rightGapRight - rightGapLeft;
    if (rightGapWidth < 0) {
      rightGapWidth = 0;
      rightGapLeft = trackWidth;
      rightGapRight = trackWidth;
    }

    const leftSegLeft = 0;
    const leftSegWidth = Math.max(0, leftGapLeft - leftSegLeft);

    const rightSegLeft = rightGapRight;
    const rightSegWidth = Math.max(0, trackWidth - rightSegLeft);

    const r = (n: number) => Math.round(n);

    const LSegLeft = r(leftSegLeft);
    const LSegWidth = r(leftSegWidth);
    const LGLeft = r(leftGapLeft);
    const LGWidth = r(leftGapWidth);
    const CLeft = r(cursorLeftFinal);
    const CWidth = r(cursorWidth);
    const RGLeft = r(rightGapLeft);
    const RGWidth = r(rightGapWidth);
    const RSegLeft = r(rightSegLeft);
    const RSegWidth = r(rightSegWidth);

    const duration = animate ? 0.66 : 0;
    const ease = "expo.out";

    gsap.killTweensOf(this._leftSeg);
    gsap.killTweensOf(this._leftGap);
    gsap.killTweensOf(this._cursorSeg);
    gsap.killTweensOf(this._rightGap);
    gsap.killTweensOf(this._rightSeg);

    gsap.to(this._leftSeg, {
      left: LSegLeft,
      width: LSegWidth,
      duration,
      ease,
    });

    gsap.to(this._leftGap, {
      left: LGLeft,
      width: LGWidth,
      duration,
      ease,
    });

    gsap.to(this._cursorSeg, {
      left: CLeft,
      width: CWidth,
      duration,
      ease,
    });

    gsap.to(this._rightGap, {
      left: RGLeft,
      width: RGWidth,
      duration,
      ease,
    });

    gsap.to(this._rightSeg, {
      left: RSegLeft,
      width: RSegWidth,
      duration,
      ease,
    });

    if (animate) {
      gsap.fromTo(
        this._cursorSeg,
        { backgroundColor: "#ffffff", boxShadow: "0 0 12px #ffffff" },
        {
          backgroundColor: "var(--c-mid)",
          boxShadow: "0 0 8px var(--c-mid)",
          duration: 2.0,
          ease: "expo.out",
        }
      );
    }
  }

  render() {
    return html`
      <div class="container">
        <div class="track">
          <div class="segment left"></div>
          <div class="gap left"></div>
          <div class="segment cursor"></div>
          <div class="gap right"></div>
          <div class="segment right"></div>
        </div>
        <div class="tabs-row">
          ${this._labels.map(
            (label, index) => html`
              <div
                class="tab ${index === this.selectedIndex ? "active" : ""}"
                @click=${() => this._select(index)}
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
