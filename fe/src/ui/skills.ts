import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { useGameStore } from "../state";
import type { SkillState } from "../state";

// --- CONSTANTS ---
const COL_WIDTH = 15;
const CHAR_MACRO_FULL = "▰";
const CHAR_MACRO_EMPTY = "▱";

@customElement("tui-skill-row")
export class TuiSkillRow extends LitElement {
  @property({ type: Object })
  skill!: SkillState;

  // Internal visual state (lerped values)
  @state() private _visTnl: number = 0;
  @state() private _visPct: number = 0;
  @state() private _visRank: number = 0;

  // Animation triggers
  @state() private _ghostActive: boolean = false;
  @state() private _flashBlockIndex: number = -1;
  @state() private _microFlashActive: boolean = false;
  @state() private _rankFlashActive: boolean = false;

  private _rafId: number | null = null;
  private _lastFrame: number = 0;
  private _ghostStartTime: number = 0;
  private _flashBlockTrigger: number = 0;
  private _microFlashTrigger: number = 0;
  private _rankFlashTrigger: number = 0;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      position: relative;
      box-sizing: border-box;
      padding: 2px 0;
    }

    /* --- GHOST OVERLAY --- */
    .ghost-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 10;
      box-sizing: border-box;
      padding: 2px 0;
      animation: ghost-fade 3s ease-out forwards;
    }

    @keyframes ghost-fade {
      0% {
        opacity: 1;
        filter: blur(0px);
      }
      20% {
        opacity: 1;
        filter: blur(0.5px);
      }
      100% {
        opacity: 0;
        filter: blur(2px);
      }
    }

    .ghost-overlay .macro-fill,
    .ghost-overlay .macro-empty {
      color: var(--c-flash) !important;
      text-shadow: 0 0 8px var(--c-flash);
    }

    .ghost-overlay .fill {
      background-color: var(--c-flash) !important;
      box-shadow: 0 0 10px var(--c-flash) !important;
      width: 100% !important;
    }

    /* Hide text in ghost to prevent bolding artifacts */
    .ghost-overlay .text-layer,
    .ghost-overlay .pct,
    .ghost-overlay .unit,
    .ghost-overlay .lvl-label {
      opacity: 0 !important;
    }

    /* --- STANDARD ELEMENTS --- */
    .text-layer,
    .rank {
      color: var(--c-mid);
    }

    .unit,
    .lvl-label {
      color: var(--c-low);
    }

    .pct {
      color: var(--c-mid);
    }

    .macro-seg {
      display: inline-block;
    }
    .macro-fill {
      color: var(--c-ember);
      transition: color 0.2s;
    }
    .macro-empty {
      color: var(--c-low);
    }

    .track {
      display: inline-block;
      width: 10ch;
      height: 1em;
      background-color: var(--c-mid);
      vertical-align: middle;
      position: relative;
      overflow: hidden;
      transform: scaleY(0.2);
      transform-origin: center;
      border-radius: 4px;
    }

    .fill {
      display: block;
      height: 100%;
      background-color: var(--c-high);
      position: relative;
      box-shadow: 0 0 4px rgba(224, 224, 224, 0.4);
    }
    .fill::after {
      content: "";
      position: absolute;
      top: 0;
      left: 97.5%;
      width: 0.575ch;
      height: 100%;
      background-color: var(--bg);
      z-index: 1;
    }

    /* --- ANIMATIONS --- */
    @keyframes rank-levelup {
      0% {
        color: var(--c-flash);
        text-shadow: 0 0 8px var(--c-flash), 0 0 12px var(--c-flash);
      }
      30% {
        /* Hold the peak brightness for ~600ms */
        color: var(--c-flash);
        text-shadow: 0 0 8px var(--c-flash), 0 0 12px var(--c-flash);
      }
      100% {
        color: var(--c-mid);
        text-shadow: none;
      }
    }
    .rank-flash,
    .rank-flash .lvl-label {
      /* Targets both the number and the "Lv" text */
      animation: rank-levelup 2s ease-out forwards;
    }

    @keyframes flash-block {
      0% {
        color: var(--c-flash);
        text-shadow: 0 0 4px var(--c-flash), 0 0 8px var(--c-flash);
      }
      100% {
        color: var(--c-ember);
        text-shadow: none;
      }
    }
    .flash-block {
      animation: flash-block 0.5s ease-out forwards;
    }

    @keyframes micro-impact {
      0% {
        background-color: var(--c-flash);
      }
      100% {
        background-color: var(--c-high);
      }
    }
    .micro-flash {
      animation: micro-impact 0.5s ease-out;
    }

    @keyframes pct-impact {
      0% {
        color: var(--c-flash);
      }
      100% {
        color: var(--c-mid);
      }
    }
    .pct-flash {
      animation: pct-impact 0.5s ease-out;
    }

    .text-layer {
      display: inline;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    if (this.skill) {
      this._visTnl = this.skill.tnl;
      this._visPct = this.skill.tnl;
      this._visRank = this.skill.rank;
    }
  }

  willUpdate(changedProps: PropertyValues) {
    if (changedProps.has("skill")) {
      this._startAnimation();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._rafId !== null) cancelAnimationFrame(this._rafId);
  }

  private _startAnimation() {
    if (this._rafId === null) {
      this._lastFrame = performance.now();
      this._rafId = requestAnimationFrame(this._tick);
    }
  }

  private _tick = (timestamp: number) => {
    if (!this.isConnected) return;

    const dt = (timestamp - this._lastFrame) / 1000;
    this._lastFrame = timestamp;

    let needsRender = false;
    let keepAnimating = false;

    // 1. Detect Level Up
    if (this.skill.rank !== this._visRank) {
      if (this.skill.rank > this._visRank) {
        this._ghostActive = true;
        this._ghostStartTime = timestamp;

        // Trigger Rank Flash
        this._rankFlashActive = true;
        this._rankFlashTrigger = timestamp;
      }
      this._visRank = this.skill.rank;
      if (this.skill.tnl < this._visTnl) {
        this._visTnl = 0;
        this._visPct = 0;
      }
      needsRender = true;
      keepAnimating = true;
    }
    // 2. Micro Flash Trigger
    if (
      this.skill.tnl > this._visTnl &&
      this.skill.tnl - this._visTnl > 0.001
    ) {
      if (timestamp - this._microFlashTrigger > 200) {
        this._microFlashTrigger = timestamp;
        this._microFlashActive = true;
        needsRender = true;
      }
    }

    // 3. Chase Physics (TNL)
    const diff = this.skill.tnl - this._visTnl;
    if (Math.abs(diff) > 0.0001) {
      const chaseSpeed = 3.0;
      this._visTnl += diff * Math.min(1, dt * chaseSpeed);
      needsRender = true;
      keepAnimating = true;
    } else {
      this._visTnl = this.skill.tnl;
    }

    // 4. Chase Physics (Text Pct)
    const textDiff = this._visTnl - this._visPct;
    if (Math.abs(textDiff) > 0.0001) {
      const textSpeed = 4.0;
      this._visPct += textDiff * Math.min(1, dt * textSpeed);
      needsRender = true;
      keepAnimating = true;
    } else {
      this._visPct = this._visTnl;
    }

    // 5. Macro Block Flash Logic (KEPT AS 10THS)
    const currentMacro = Math.floor(this._visTnl * 10);
    const prevMacro = Math.floor((this._visTnl - diff * 0.1) * 10);

    if (currentMacro > prevMacro && this._visTnl < 0.99) {
      this._flashBlockIndex = currentMacro - 1;
      this._flashBlockTrigger = timestamp;
      needsRender = true;
    }

    // 6. Ghost Cleanup
    if (this._ghostActive) {
      if (timestamp - this._ghostStartTime > 3000) {
        this._ghostActive = false;
        needsRender = true;
      } else {
        keepAnimating = true;
      }
    }
    // 7. Rank Flash Cleanup
    if (this._rankFlashActive) {
      if (timestamp - this._rankFlashTrigger > 2000) {
        // 2 seconds
        this._rankFlashActive = false;
        needsRender = true;
      } else {
        keepAnimating = true;
      }
    }
    // 7. Flash Cleanup
    if (timestamp - this._flashBlockTrigger < 600) keepAnimating = true;
    if (timestamp - this._microFlashTrigger < 250) {
      keepAnimating = true;
    } else {
      this._microFlashActive = false;
    }

    if (needsRender) {
      // Lit handles update
    }

    if (keepAnimating) {
      this._rafId = requestAnimationFrame(this._tick);
    } else {
      this._rafId = null;
    }
  };

  render() {
    const now = performance.now();
    let ghostLayer = html``;

    if (this._ghostActive) {
      // prettier-ignore
      ghostLayer = html`<div class="ghost-overlay">${this.renderBarLayout(1.0, 1.0, this._visRank, true, now)}</div>`;
    }

    return html`${ghostLayer}${this.renderBarLayout(
      this._visTnl,
      this._visPct,
      this._visRank,
      false,
      now
    )}`;
  }

  private renderBarLayout(
    tnl: number,
    pctTnl: number,
    rankVal: number,
    isGhost: boolean,
    now: number
  ) {
    const safeTnl = Math.max(0, Math.min(1, tnl));
    const safePctTnl = Math.max(0, Math.min(1, pctTnl));

    let microPct =
      safeTnl >= 0.999 ? 100.0 : (safeTnl * 4 - Math.floor(safeTnl * 4)) * 100;

    if (isGhost) microPct = 100.0;
    const microPctStr = microPct.toFixed(2);

    const pctValue = Math.floor(safePctTnl * 100);
    const pctNumStr = pctValue.toString().padStart(3, " ");
    const rankStr = rankVal.toString().padStart(3, " ");
    const namePadded = this.skill.name.padStart(COL_WIDTH, " ");

    const statsStr = `Lv ${rankStr} ${pctNumStr}%`;
    const padding = " ".repeat(Math.max(0, COL_WIDTH - statsStr.length));

    const macroSpans = [];
    const flashingBlockIdx =
      now - this._flashBlockTrigger < 600 ? this._flashBlockIndex : -1;
    const macroCount = Math.floor(safeTnl * 10);

    for (let i = 0; i < 10; i++) {
      let className = "macro-empty";
      let char = CHAR_MACRO_EMPTY;

      if (isGhost || i < macroCount || safeTnl >= 0.999) {
        className = "macro-fill";
        char = CHAR_MACRO_FULL;
        if (!isGhost && i === flashingBlockIdx) className += " flash-block";
      }
      // prettier-ignore
      macroSpans.push(html`<span class="macro-seg ${className}">${char}</span>`);
    }

    const isMicroFlashing = !isGhost && this._microFlashActive;
    const fillClass = isMicroFlashing ? "fill micro-flash" : "fill";
    const pctClass = isMicroFlashing
      ? "pct text-layer pct-flash"
      : "pct text-layer";
    const rankClass =
      !isGhost && this._rankFlashActive ? "rank rank-flash" : "rank";
    // prettier-ignore
    return html`<div><span class="text-layer">${namePadded}</span>  ${macroSpans}</div><div><span class="text-layer">${padding}</span><span class="${rankClass}"><span class="lvl-label">Lv</span> ${rankStr}</span> <span class="${pctClass}">${pctNumStr}</span><span class="unit">%</span>  <span class="track"><span class="${fillClass}" style="width: ${microPctStr}%"></span></span></div>`;
  }
}

/**
 * TuiSkills (Container)
 */
@customElement("tui-skills")
export class TuiSkills extends LitElement {
  @state()
  private skills: SkillState[] = [];

  private _unsub: (() => void) | null = null;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      /* --- THEME: LOW CONTRAST EMBER --- */
      --bg: #050505;
      --c-high: #e0e0e0;
      --c-mid: #9e9e9e;
      --c-low: #555555;
      --c-void: #333333;
      --c-ember: #db5800;
      --c-flash: #fff5e6;

      font-family: "IBM Plex Mono", monospace;
      white-space: pre;
      line-height: 1.2;
      font-weight: 400;
      color: var(--c-mid);
    }

    .container {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(27ch, 1fr));
      gap: 2ch 1ch;
      align-items: start;
      justify-content: start;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    this.skills = useGameStore.getState().skills;
    this._unsub = useGameStore.subscribe((state) => {
      if (state.skills !== this.skills) {
        this.skills = state.skills;
      }
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._unsub) this._unsub();
  }

  render() {
    return html`
      <div class="container">
        ${this.skills.map(
          (skill) => html`<tui-skill-row .skill=${skill}></tui-skill-row>`
        )}
      </div>
    `;
  }
}
