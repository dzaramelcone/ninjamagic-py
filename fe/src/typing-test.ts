/**
 * A highly interactive and animated typing test web component.
 *
 * This component provides a full-featured typing test experience, using Lit for
 * reactive state management and GSAP for high-performance, fluid animations.
 * It is designed to be self-contained, accessible, and visually engaging.
 *
 * @customElement typing-test
 *
 * @property {string} phrase - The text phrase for the user to type.
 * @property {number} spawnStagger - The delay (in seconds) between each character appearing in the intro animation.
 * @property {DissolveType} correctDissolveType - The dissolve animation to play for correctly completed words ('fade' or 'wave').
 * @property {DissolveType} errorDissolveType - The dissolve animation for incorrect words (Note: this is overridden by the shatter effect for locked-in words).
 * @property {string} keySoundUrl - An optional URL for a sound to play on correct key presses.
 * @property {string} errorSoundUrl - An optional URL for a sound to play on incorrect key presses.
 *
 * @fires test-complete - Dispatched when the user successfully types the entire phrase.
 *
 * @cssprop [--typing-color-pending=#888] - Color of pending text.
 * @cssprop [--typing-color-correct=#333] - Color of correctly typed text.
 * @cssprop [--typing-color-incorrect=#e00] - Color of incorrectly typed text.
 * @cssprop [--typing-bg-incorrect=#fdd] - Background color for incorrectly typed characters.
 * @cssprop [--typing-cursor-color=#333] - Color of the blinking cursor.
 *
 * --- FEATURES ---
 *
 * - **Animated Introduction:** Glyphs gracefully slide in from the right with a staggered effect upon loading.
 *
 * - **Realistic Typing Flow:** The cursor advances even on incorrect input, allowing the user to continue typing and fix mistakes with the backspace key, mimicking a real text editor.
 *
 * - **Advanced Word Completion Logic:**
 * - Correctly typed words play a "dissolve" animation and disappear.
 * - Incorrectly typed words are marked with a wavy red underline.
 * - Once a subsequent *correct* word is completed, any previous incorrect words become permanently un-editable and "shatter" off-screen for powerful visual feedback.
 *
 * - **Robust State Management:**
 * - A race condition-proof locking mechanism prevents users from backspacing into correctly completed words, no matter how quickly they type.
 *
 * - **Layout Shift Prevention (Jank-Free):**
 * - Completed words are hidden using a method that preserves their space, preventing the remaining text from jumping.
 * - Upon test completion, the entire component smoothly animates its height to zero before being removed, ensuring the parent container does not abruptly resize.
 *
 * - **Enhanced User Experience:**
 * - The component is focusable and ready for input immediately, even during the intro animation.
 * - Focus is subtly indicated by the presence of the blinking cursor, with no distracting outlines or box shadows.
 */

import { LitElement, html, css, type PropertyValues, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import gsap from "gsap";
import { CSSPlugin } from "gsap/CSSPlugin";

gsap.registerPlugin(CSSPlugin);

// --- Type Definitions ---
type GlyphStatus = "pending" | "correct" | "incorrect" | "dissolved";
type DissolveType = "fade" | "wave" | "scatter" | "shatter";

interface Glyph {
  char: string;
  status: GlyphStatus;
  wordIndex: number;
  glyphIndex: number;
}

interface Word {
  word: Glyph[];
  isComplete: boolean;
  isCorrect: boolean;
  isLocked: boolean; // FIX: New state to prevent race conditions
}

@customElement("typing-test")
export class TypingTest extends LitElement {
  // --- Reactive Properties ---
  @property({ type: String }) phrase: string;
  @property({ type: Number, attribute: "spawn-stagger" }) spawnStagger: number;
  @property({ type: String, attribute: "correct-dissolve-type" })
  correctDissolveType: DissolveType;
  @property({ type: String, attribute: "error-dissolve-type" })
  errorDissolveType: DissolveType;
  @property({ type: String, attribute: "key-sound-url" }) keySoundUrl: string;
  @property({ type: String, attribute: "error-sound-url" })
  errorSoundUrl: string;

  @state() private _words: Word[];
  @state() private _activeWordIndex: number;
  @state() private _activeGlyphIndex: number;
  @state() private _isTestComplete: boolean;
  @state() private _isReadyForRemoval: boolean = false;

  // --- Non-Reactive Properties ---
  private _keySound: HTMLAudioElement | null = null;
  private _errorSound: HTMLAudioElement | null = null;
  private _cursorTween: gsap.core.Tween | null = null;
  private _activeTimeline: gsap.core.Timeline | null = null;

  private get _cursorElement(): HTMLElement | null {
    return this.renderRoot.querySelector(".cursor") as HTMLElement | null;
  }

  constructor() {
    super();
    this.phrase = "The quick brown fox jumps over the lazy dog.";
    this.spawnStagger = 0.05;
    this.correctDissolveType = "fade";
    this.errorDissolveType = "scatter";
    this.keySoundUrl = "";
    this.errorSoundUrl = "";
    this._words = [];
    this._activeWordIndex = 0;
    this._activeGlyphIndex = 0;
    this._isTestComplete = false;
    this.tabIndex = 0;
  }

  protected willUpdate(changedProperties: PropertyValues): void {
    if (changedProperties.has("phrase") && this.phrase) {
      this._parsePhrase(this.phrase);
    }
    if (changedProperties.has("keySoundUrl")) {
      this._loadAudio(this.keySoundUrl, "_keySound");
    }
    if (changedProperties.has("errorSoundUrl")) {
      this._loadAudio(this.errorSoundUrl, "_errorSound");
    }
    if (
      changedProperties.has("_activeGlyphIndex") ||
      changedProperties.has("_activeWordIndex")
    ) {
      this._updateActiveGlyphPosition();
    }
  }

  protected firstUpdated(): void {
    const glyphs = this.renderRoot.querySelectorAll(".glyph");
    const container = this.renderRoot.querySelector(
      ".typing-container"
    ) as HTMLElement;

    this.addEventListener("keydown", this._handleKeydown);
    this.focus();
    this._updateActiveGlyphPosition(true);

    if (container) container.style.overflowX = "hidden";
    gsap.from(glyphs, {
      duration: 1,
      x: 300,
      opacity: 0,
      ease: "power4.out",
      stagger: this.spawnStagger,
      onComplete: () => {
        if (container) container.style.overflowX = "visible";
      },
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.removeEventListener("keydown", this._handleKeydown);
    if (this._cursorTween) this._cursorTween.kill();
    if (this._activeTimeline) this._activeTimeline.kill();
    gsap.killTweensOf(this.renderRoot.querySelectorAll(".glyph"));
    gsap.killTweensOf(this.renderRoot.querySelector(".cursor"));
    this._keySound = null;
    this._errorSound = null;
  }

  private _parsePhrase(phrase: string): void {
    const wordStrings = phrase.trim().split(/\s+/);
    const words = wordStrings.map((wordStr, wIndex) => {
      const glyphs: Glyph[] = wordStr.split("").map((char, gIndex) => ({
        char,
        status: "pending" as GlyphStatus,
        wordIndex: wIndex,
        glyphIndex: gIndex,
      }));

      if (wIndex < wordStrings.length - 1) {
        glyphs.push({
          char: " ",
          status: "pending" as GlyphStatus,
          wordIndex: wIndex,
          glyphIndex: glyphs.length,
        });
      }

      return {
        word: glyphs,
        isComplete: false,
        isCorrect: true,
        isLocked: false,
      }; // FIX: Initialize isLocked state
    });

    this._words = words;
    this._activeWordIndex = 0;
    this._activeGlyphIndex = 0;
  }

  private _loadAudio(
    url: string,
    targetKey: "_keySound" | "_errorSound"
  ): void {
    if (url) {
      this[targetKey] = new Audio(url);
      this[targetKey]?.load();
    } else {
      this[targetKey] = null;
    }
  }

  private _playSound(audioElement: HTMLAudioElement | null): void {
    if (audioElement) {
      audioElement.currentTime = 0;
      audioElement
        .play()
        .catch((e) => console.warn("Audio playback failed:", e));
    }
  }

  private _handleKeydown = (event: KeyboardEvent): void => {
    if (event.ctrlKey || event.altKey || event.metaKey) {
      return;
    }
    event.preventDefault();

    const activeWord = this._words[this._activeWordIndex];
    if (!activeWord) return;

    const isAtEndOfWord = this._activeGlyphIndex >= activeWord.word.length;
    if (isAtEndOfWord && event.key !== "Backspace") {
      return;
    }

    const expectedGlyph = activeWord.word[this._activeGlyphIndex];
    if (expectedGlyph && event.key.length === 1) {
      if (event.key === " " && expectedGlyph.char === " ") {
        this._handleWordTransition(activeWord);
      } else if (event.key === expectedGlyph.char) {
        this._handleCorrectInput(activeWord, expectedGlyph);
      } else {
        this._handleIncorrectInput(activeWord, expectedGlyph);
      }
    } else if (event.key === "Backspace") {
      this._handleBackspace();
    }
    this.requestUpdate();
  };

  private _handleCorrectInput(activeWord: Word, expectedGlyph: Glyph): void {
    this._playSound(this._keySound);
    expectedGlyph.status = "correct";

    const isLastGlyphOfPhrase =
      this._activeWordIndex === this._words.length - 1 &&
      this._activeGlyphIndex === activeWord.word.length - 1;

    if (isLastGlyphOfPhrase) {
      this._handleTestCompletion();
    } else {
      this._activeGlyphIndex++;
    }
  }

  private _handleIncorrectInput(activeWord: Word, expectedGlyph: Glyph): void {
    if (expectedGlyph.status === "pending") {
      this._playSound(this._errorSound);
      activeWord.isCorrect = false;
      expectedGlyph.status = "incorrect";
      this._activeGlyphIndex++;
    }
  }

  private _handleBackspace(): void {
    if (this._activeGlyphIndex === 0 && this._activeWordIndex === 0) return;

    if (this._activeGlyphIndex > 0) {
      this._activeGlyphIndex--;
    } else if (this._activeWordIndex > 0) {
      const prevWord = this._words[this._activeWordIndex - 1];

      // FIX: Check the isLocked property. This is now set instantly and prevents the race condition.
      if (prevWord.isLocked) {
        return;
      }

      this._activeWordIndex--;
      this._activeGlyphIndex = prevWord.word.length - 1;
      prevWord.isComplete = false;
    }

    const glyphToReset =
      this._words[this._activeWordIndex].word[this._activeGlyphIndex];
    if (glyphToReset?.status !== "dissolved") {
      glyphToReset.status = "pending";
    }

    const currentWord = this._words[this._activeWordIndex];
    currentWord.isCorrect = currentWord.word.every(
      (g) => g.status === "pending" || g.status === "correct"
    );
  }

  private _handleWordTransition(currentWord: Word): void {
    const spaceGlyph = currentWord.word[this._activeGlyphIndex];
    if (spaceGlyph?.char === " ") {
      spaceGlyph.status = "correct";
    }

    this._playSound(this._keySound);
    this._handleWordCompletion(currentWord.isCorrect, this._activeWordIndex);

    if (this._activeWordIndex < this._words.length - 1) {
      this._activeWordIndex++;
      this._activeGlyphIndex = 0;
    }
  }

  private _handleTestCompletion(): void {
    this._isTestComplete = true;
    this.removeEventListener("keydown", this._handleKeydown);
    this.dispatchEvent(
      new CustomEvent("test-complete", { bubbles: true, composed: true })
    );

    this._animateCollapse();
  }

  private _updateActiveGlyphPosition(
    isInitialPlacement: boolean = false
  ): void {
    if (!this._cursorElement) return;

    const activeGlyphSelector = `.glyph[data-word-index="${this._activeWordIndex}"][data-glyph-index="${this._activeGlyphIndex}"]`;
    let targetGlyph = this.renderRoot.querySelector(
      activeGlyphSelector
    ) as HTMLElement;

    if (!targetGlyph) return;

    const containerRect = (
      this.renderRoot.querySelector(".typing-container") as HTMLElement
    ).getBoundingClientRect();
    const glyphRect = targetGlyph.getBoundingClientRect();
    const targetX = glyphRect.left - containerRect.left;
    const targetY = glyphRect.top - containerRect.top;
    const duration = isInitialPlacement ? 0 : 0.15;

    if (this._cursorTween) this._cursorTween.kill();
    this._cursorTween = gsap.to(this._cursorElement, {
      duration,
      x: targetX,
      y: targetY,
      height: glyphRect.height,
      force3D: true,
      ease: "power2.out",
    });
  }
  // New helper method to handle the shatter effect
  private _triggerShatterOnWord(wordIndex: number): void {
    const wordElement = this.renderRoot.querySelector(
      `.word-container[data-word-index="${wordIndex}"]`
    ) as HTMLElement;
    if (!wordElement) return;

    // Immediately remove the underline before the animation starts
    wordElement.style.textDecoration = "none";

    const glyphs = Array.from(
      wordElement.querySelectorAll(".glyph")
    ) as HTMLElement[];
    if (glyphs.length === 0) return;

    // Play the animation and hide the word container when it's done
    this._animateShatter(glyphs).eventCallback("onComplete", () => {
      wordElement.style.visibility = "hidden";
    });
  }

  // Updated method to trigger the shatter effect
  private _handleWordCompletion(wasCorrect: boolean, wordIndex: number): void {
    const word = this._words[wordIndex];
    if (!word) return;

    if (wasCorrect) {
      // Lock the current correct word instantly.
      word.isLocked = true;

      // NEW: Look backwards for any incorrect words that are now permanently wrong.
      for (let i = wordIndex - 1; i >= 0; i--) {
        const prevWord = this._words[i];

        // If we hit a word that was already locked, we can stop.
        if (prevWord.isLocked) break;

        // If we find an incorrect word, lock it and shatter it.
        if (!prevWord.isCorrect) {
          prevWord.isLocked = true;
          this._triggerShatterOnWord(i);
        }
      }
    }

    // This handles the visual state of the *current* word.
    if (!wasCorrect) {
      word.isComplete = true;
      this.requestUpdate();
      return;
    }

    // This is the original animation logic for the *current* correct word.
    const glyphs = Array.from(
      this.renderRoot.querySelectorAll(`.glyph[data-word-index="${wordIndex}"]`)
    ) as HTMLElement[];
    if (glyphs.length === 0) return;

    const animationFunction =
      this.correctDissolveType === "wave"
        ? this._animateWave
        : this._animateFade;
    this._activeTimeline = animationFunction.bind(this)(glyphs);
    this._activeTimeline.eventCallback("onComplete", () => {
      word.isComplete = true;
      word.word.forEach((g) => (g.status = "dissolved"));
      this.requestUpdate();

      if (wordIndex === this._words.length - 1) {
        this._isTestComplete = true;
        this.removeEventListener("keydown", this._handleKeydown);
        this.dispatchEvent(
          new CustomEvent("test-complete", { bubbles: true, composed: true })
        );
      }
      this._activeTimeline = null;
    });
  }
  private _animateFade = (targets: HTMLElement[]) =>
    gsap
      .timeline()
      .to(targets, { duration: 0.3, opacity: 0, ease: "power1.in" });
  private _animateWave = (targets: HTMLElement[]) =>
    gsap.timeline().to(targets, {
      duration: 0.5,
      opacity: 0,
      y: -10,
      scale: 0.9,
      stagger: 0.02,
      ease: "power2.inOut",
    });
  private _animateScatter = (targets: HTMLElement[]) =>
    gsap.timeline().to(targets, {
      duration: 0.6,
      x: () => gsap.utils.random(-150, 150),
      y: () => gsap.utils.random(-80, 80),
      rotation: () => gsap.utils.random(-90, 90),
      opacity: 0,
      stagger: 0.01,
      ease: "power3.out",
      force3D: true,
    });
  private _animateShatter = (targets: HTMLElement[]) =>
    gsap.timeline().to(targets, {
      duration: 0.2,
      scale: 0.1,
      rotation: () => gsap.utils.random(-180, 180),
      x: () => gsap.utils.random(-50, 50),
      y: () => gsap.utils.random(-50, 50),
      opacity: 0,
      ease: "power4.in",
      force3D: true,
    });
  private _animateCollapse(): void {
    gsap.to(this, {
      duration: 0.5,
      height: 0,
      opacity: 0,
      paddingTop: 0,
      paddingBottom: 0,
      marginTop: 0,
      marginBottom: 0,
      ease: "power2.in",
      onComplete: () => {
        // After the animation is done, set the state to trigger final removal
        this._isReadyForRemoval = true;
      },
    });
  }

  private _getWordContainerClass(word: Word): string {
    // Visual completion is still tied to `isComplete`
    if (!word.isComplete) return "";
    return word.isCorrect ? "completed-correct" : "completed-incorrect";
  }

  render() {
    if (this._isReadyForRemoval) {
      return nothing;
    }

    return html`
      <div class="typing-container" ?disabled=${this._isTestComplete}>
        <div class="phrase-output">
          ${this._words.map(
            (wordObj) => html` <span
              class="word-container ${this._getWordContainerClass(wordObj)}"
              data-word-index="${wordObj.word[0].wordIndex}"
            >
              ${wordObj.word.map(
                (glyph) => html`<span
                  class="glyph"
                  data-status="${glyph.status}"
                  data-word-index="${glyph.wordIndex}"
                  data-glyph-index="${glyph.glyphIndex}"
                  >${glyph.char === " " ? html`&nbsp;` : glyph.char}</span
                >`
              )}
            </span>`
          )}
        </div>
        <div class="cursor"></div>
      </div>
    `;
  }

  static styles = css`
    :host {
      display: block;
      font-size: 24px;
      font-family: monospace;
      line-height: 1.5;
      user-select: none;
      overflow: hidden;
      padding: 20px;
      outline: none;
    }
    .typing-container {
      position: relative;
      min-height: 100px;
      outline: none;
    }
    .word-container {
      display: inline-block;
      white-space: nowrap;
      font-size: 0;
    }
    .word-container.completed-correct {
      visibility: hidden;
    }
    .word-container.completed-incorrect {
      text-decoration: underline wavy var(--typing-color-incorrect, #e00);
      text-underline-offset: 4px;
    }
    .glyph {
      display: inline-block;
      font-size: 24px;
      transition: color 0.1s ease;
      color: var(--typing-color-pending, #888);
    }
    .glyph[data-status="correct"] {
      color: var(--typing-color-correct, #333);
    }
    .glyph[data-status="incorrect"] {
      color: var(--typing-color-incorrect, #e00);
      background-color: var(--typing-bg-incorrect, #fdd);
    }
    .cursor {
      position: absolute;
      top: 0;
      left: 0;
      background-color: var(--typing-cursor-color, #333);
      width: 2px;
      height: 1.5em;
      animation: blink 1s step-end infinite;
      pointer-events: none;
      will-change: transform;
      display: none;
    }
    :host(:focus-within) .cursor {
      display: block;
    }
    @keyframes blink {
      from,
      to {
        opacity: 1;
      }
      50% {
        opacity: 0;
      }
    }
  `;
}
