// src/ui/tui-prompt.ts
import { LitElement, html, css } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import "./tui-micro-bar";

@customElement("tui-prompt")
export class TuiPrompt extends LitElement {
  @property({ type: String, attribute: "text", reflect: true })
  text: string = "";

  @state() private timerValue: number = 1; // 0-1 for micro-bar
  @state() private hasTiming: boolean = false;

  @query("slot") private slotEl!: HTMLSlotElement;
  @query(".overlay") private overlayEl!: HTMLElement;
  @query(".typed") private typedEl!: HTMLSpanElement;
  @query(".prompt") private promptEl!: HTMLSpanElement;
  @query(".caret") private caretEl!: HTMLSpanElement;

  private input: HTMLInputElement | null = null;
  private ro: ResizeObserver | null = null;
  private countdownInterval: number | null = null;

  private charW = 0;
  private padL = 0;

  private get isActive(): boolean {
    return (this.text ?? "").length > 0;
  }

  static styles = css`
    :host {
      display: block;
      position: relative;
      width: 100%;
    }

    .wrap {
      position: relative;
      width: 100%;
    }

    /* Real input remains authoritative for focus/keyboard.
       We ALWAYS disable native caret; our overlay caret is the caret. */
    ::slotted(input) {
      width: 100%;
      background: transparent;
      position: relative;
      z-index: 1;

      color: inherit;
      caret-color: transparent; /* always off */
    }

    /* When prompt is active, we hide the input text (overlay becomes the view). */
    :host([text]:not([text=""])) ::slotted(input) {
      color: transparent;
    }
    .overlay {
      position: absolute;
      inset: 0;
      pointer-events: none;
      white-space: pre;
      overflow: hidden;
      display: flex;
      align-items: center;
    }

    .typed {
      opacity: var(--tui-typed-opacity, 1);
    }

    .prompt {
      opacity: var(--tui-prompt-opacity, 0.35);
    }

    /* When prompt is NOT active, hide the typed/prompt glyphs (caret stays). */
    :host(:not([text])) .typed,
    :host(:not([text])) .prompt,
    :host([text=""]) .typed,
    :host([text=""]) .prompt {
      display: none;
    }

    .ch {
    }

    .match {
      color: var(--tui-match-color, #2fd27c);
    }
    .mismatch {
      color: var(--tui-mismatch-color, #ff4d4d);
    }
    .extra {
      color: var(--tui-extra-color, #ff4d4d);
    }
    .remain {
      color: var(--tui-prompt-color, currentColor);
    }

    .caret {
      color: var(--primary);
      position: absolute;
      left: 0;
      top: 50%;
      transform: translate(
        var(--caret-x, 0px),
        calc(-50% + var(--caret-y, 0px))
      );

      width: var(--caret-w, 2px);
      height: var(--caret-h, 1.25em);
      background: var(--tui-caret-color, currentColor);
      border-radius: 1px;

      animation: caret-blink var(--caret-blink-ms, 1000ms) steps(1) infinite;
      transition: transform var(--caret-move-ms, 370ms)
          cubic-bezier(0.16, 1, 0.3, 1),
        opacity 120ms linear;
      will-change: transform;
    }

    @keyframes caret-blink {
      0%,
      49% {
        opacity: 1;
      }
      50%,
      100% {
        opacity: 0.35;
      }
    }

    .timer-bar {
      position: absolute;
      right: 0.5ch;
      top: 50%;
      transform: translateY(-50%);
      --tui-micro-bar-width: 6ch;
      --tui-duration: 0.2s;
      --tui-ease: linear;
      --tui-monotonic: decrease;
    }

    .timer-bar[hidden] {
      display: none;
    }
  `;

  render() {
    return html`
      <div class="wrap">
        <div class="overlay" aria-hidden="true">
          <span class="typed"></span><span class="prompt"></span>
          <span class="caret"></span>
        </div>
        <tui-micro-bar
          class="timer-bar"
          .value=${this.timerValue}
          ?hidden=${!this.hasTiming}
        ></tui-micro-bar>
        <slot @slotchange=${this.onSlotChange}></slot>
      </div>
    `;
  }

  firstUpdated() {
    this.onSlotChange();
  }

  updated(changed: Map<string, unknown>) {
    if (changed.has("text")) {
      this.renderOverlay();
    }
  }

  /** Public API */
  setPrompt(t: string, end?: number, serverTime?: number) {
    this.text = t ?? "";
    if (!this.text) this.removeAttribute("text");

    this.stopCountdown();

    if (end && serverTime) {
      const ttlSeconds = end - serverTime;
      if (ttlSeconds > 0) {
        this.startCountdown(ttlSeconds * 1000);
      }
    }

    queueMicrotask(() => this.renderOverlay());
  }

  clearPrompt() {
    this.text = "";
    this.removeAttribute("text");
    this.stopCountdown();
    this.renderOverlay();
  }

  private startCountdown(ttlMs: number) {
    this.hasTiming = true;

    // Set animation duration to match TTL, then animate from 1→0 once
    const timerBar = this.shadowRoot?.querySelector(
      ".timer-bar"
    ) as HTMLElement | null;
    if (timerBar) {
      timerBar.style.setProperty("--tui-duration", `${ttlMs}ms`);
    }

    // Start at full, then drop to 0 - single smooth animation
    this.timerValue = 1;
    requestAnimationFrame(() => {
      this.timerValue = 0;
    });

    // Clear prompt when timer expires
    this.countdownInterval = window.setTimeout(() => {
      this.clearPrompt();
    }, ttlMs);
  }

  private stopCountdown() {
    if (this.countdownInterval !== null) {
      clearTimeout(this.countdownInterval);
      this.countdownInterval = null;
    }
    this.hasTiming = false;
    this.timerValue = 1;
  }

  private onSlotChange = () => {
    const assigned = this.slotEl
      ?.assignedElements({ flatten: true })
      .find((el) => el instanceof HTMLInputElement) as
      | HTMLInputElement
      | undefined;

    this.input =
      assigned ?? (this.querySelector("input#cmd") as HTMLInputElement | null);

    if (!this.input) {
      console.warn("<tui-prompt> requires a child <input id='cmd'>");
      return;
    }

    this.attachInputListeners();
    this.syncStylesFromInput();
    this.renderOverlay();
  };

  private attachInputListeners() {
    if (!this.input) return;

    this.input.removeEventListener("input", this.onInput);
    this.input.removeEventListener("keydown", this.onKeydown);
    this.input.removeEventListener("keyup", this.onKeyup);
    this.input.removeEventListener("click", this.onClickOrSelect);
    this.input.removeEventListener("select", this.onClickOrSelect);
    this.input.removeEventListener("scroll", this.onScroll);

    this.input.addEventListener("input", this.onInput);
    this.input.addEventListener("keydown", this.onKeydown);
    this.input.addEventListener("keyup", this.onKeyup);
    this.input.addEventListener("click", this.onClickOrSelect);
    this.input.addEventListener("select", this.onClickOrSelect);
    this.input.addEventListener("scroll", this.onScroll);

    if (!this.ro) {
      this.ro = new ResizeObserver(() => {
        this.syncStylesFromInput();
        this.renderOverlay();
      });
      this.ro.observe(this.input);
    }
  }

  private onInput = () => this.renderOverlay();
  private syncAfterEnter() {
    // Next frame: after all key handlers + DOM mutations + layout settle.
    requestAnimationFrame(() => {
      // If chat.ts cleared the field, force cursor to column 0.
      if (this.input?.value === "") {
        this.caretEl.style.setProperty("--caret-x", "0px");
      }
      this.renderOverlay();
    });
  }
  private onScroll = () => {
    // caret alignment depends on scrollLeft
    this.updateCaretFromInput();
  };

  private onKeydown = (e: KeyboardEvent) => {
    // Clear prompt on Enter (view state). chat.ts sends/clears input.value.
    if (e.key === "Enter") {
      // If we were in prompt mode, clear prompt immediately.
      // (We do NOT try to position caret right now — chat.ts may clear input.value after us.)
      if (this.isActive) this.clearPrompt();

      this.syncAfterEnter();
      return;
    }
    if (
      e.key === "ArrowLeft" ||
      e.key === "ArrowRight" ||
      e.key === "Home" ||
      e.key === "End"
    ) {
      requestAnimationFrame(() => this.updateCaretFromInput());
    }

    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      queueMicrotask(() => this.renderOverlay());
    }
  };

  private onKeyup = (e: KeyboardEvent) => {
    if (e.key === "ArrowUp" || e.key === "ArrowDown") this.renderOverlay();
  };

  private onClickOrSelect = () => {
    // When prompt inactive, we want caret to follow click/selection.
    // When prompt active, you can choose typed-end behavior; we keep typed-end.
    this.renderOverlay();
  };

  private recomputeMetrics() {
    if (!this.input) return;

    const cs = getComputedStyle(this.input);
    this.padL = parseFloat(cs.paddingLeft || "0");

    // Measure monospace glyph width (10 chars reduces rounding error)
    const probe = document.createElement("span");
    probe.textContent = "MMMMMMMMMM";
    probe.style.position = "absolute";
    probe.style.visibility = "hidden";
    probe.style.whiteSpace = "pre";
    probe.style.fontFamily = cs.fontFamily;
    probe.style.fontSize = cs.fontSize;
    probe.style.fontWeight = cs.fontWeight;
    probe.style.letterSpacing = cs.letterSpacing;
    probe.style.lineHeight = cs.lineHeight;
    document.body.appendChild(probe);

    const w = probe.getBoundingClientRect().width;
    document.body.removeChild(probe);

    this.charW = w / 10;
  }

  private syncStylesFromInput() {
    if (!this.input) return;

    const cs = getComputedStyle(this.input);

    // Keep overlay text layout matched to input
    this.overlayEl.style.fontFamily = cs.fontFamily;
    this.overlayEl.style.fontSize = cs.fontSize;
    this.overlayEl.style.fontWeight = cs.fontWeight;
    this.overlayEl.style.letterSpacing = cs.letterSpacing;
    this.overlayEl.style.lineHeight = cs.lineHeight;
    this.overlayEl.style.padding = cs.padding;
    this.overlayEl.style.textAlign = cs.textAlign;

    this.recomputeMetrics();
  }

  private renderOverlay() {
    if (!this.input) return;

    if (this.isActive) {
      // Render typed + prompt spans only when active
      const prompt = this.text ?? "";
      const typed = this.input.value ?? "";

      const typedFrag = document.createDocumentFragment();
      for (let i = 0; i < typed.length; i++) {
        const span = document.createElement("span");
        span.classList.add("ch");

        if (i >= prompt.length) span.classList.add("extra");
        else if (typed[i] === prompt[i]) span.classList.add("match");
        else span.classList.add("mismatch");

        span.textContent = typed[i];
        typedFrag.appendChild(span);
      }

      const promptFrag = document.createDocumentFragment();
      for (let i = typed.length; i < prompt.length; i++) {
        const span = document.createElement("span");
        span.classList.add("ch", "remain");
        span.textContent = prompt[i];
        promptFrag.appendChild(span);
      }

      this.typedEl.replaceChildren(typedFrag);
      this.promptEl.replaceChildren(promptFrag);

      this.updateCaretFromInput();
      return;
    }

    // In normal mode, no overlay text—only caret.
    this.typedEl.textContent = "";
    this.promptEl.textContent = "";

    // In normal mode, caret should behave like native: follow selection.
    this.updateCaretFromInput();
  }

  private updateCaretFromInput() {
    if (!this.input) return;

    const idx = this.input.selectionStart ?? this.input.value.length;

    const x = this.padL + idx * this.charW - (this.input.scrollLeft || 0);
    this.caretEl.style.setProperty("--caret-x", `${Math.max(0, x)}px`);
  }
}
