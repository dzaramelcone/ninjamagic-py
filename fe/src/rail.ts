// rail.ts — Multi-rail beat typing (stable soft/hard switches, pristine restore, safe mirroring)

type Grade = "perfect" | "great" | "good" | "poor" | "miss";

/* -------------------- Tunables -------------------- */
const BPM = 160;
const DWELL_MS = 60000 / BPM;

const NEXT_OFFSET_CH = 6;
const WORDS_VISIBLE = 3;
const WORD_GAP_CH = 1.4;

const LOGICAL_EXPAND_CH_LEFT = 0.9;
const LOGICAL_EXPAND_CH_RIGHT = 0.9;
const STOP_MARGIN_CH = 0.6;

const BOX_PERFECT_FRAC = 0.4;
const BOX_GREAT_FRAC = 0.8;

const RAIL_COUNT = 3;
const GATE_W_CH = 2.5;

/* -------------------- Lexicon -------------------- */
const LEXICON = [
  "cleave",
  "sunder",
  "clash",
  "clangor",
  "shieldwall",
  "warband",
  "longblade",
  "broadsword",
  "falchion",
  "glaive",
  "halberd",
  "bardiche",
  "buckler",
  "mailcoat",
  "hauberk",
  "vambrace",
  "cuirass",
  "greaves",
  "gauntlet",
  "bastion",
  "portcullis",
  "battlement",
  "merlon",
  "crenel",
  "parapet",
  "drawbridge",
  "motte",
  "bailey",
  "muster",
  "vanguard",
  "rearguard",
  "banneret",
  "standard",
  "pennon",
  "pike",
  "lance",
  "javelin",
  "slingstone",
  "warhorn",
  "warcry",
  "skirmish",
  "melee",
  "fray",
  "foray",
  "batteringram",
  "mangonel",
  "trebuchet",
  "ballista",
  "salvo",
  "volley",
  "caltrop",
  "ambush",
  "rout",
  "siege",
  "sortie",
  "sapper",
  "steelbright",
  "grim",
  "wrath",
  "valor",
  "fealty",
  "thane",
  "huscarl",
  "shieldmaiden",
  "warlord",
  "chieftain",
  "marshal",
  "squire",
  "knight",
  "paladin",
  "pikeman",
  "bowman",
  "archer",
  "crossbow",
  "quarrel",
  "arrowstorm",
  "fletch",
  "nock",
  "loose",
  "warpath",
];
function pickWord() {
  return LEXICON[Math.floor(Math.random() * LEXICON.length)];
}

/* -------------------- DOM refs -------------------- */
const trackEl = document.getElementById("track") as HTMLDivElement;
const railsEl = document.getElementById("rails") as HTMLDivElement;
const gateBoxEl = document.getElementById("gateBox") as HTMLDivElement;
const feedbackEl = document.getElementById("feedback") as HTMLDivElement;

/* -------------------- Audio Context -------------------- */
let actx: AudioContext | null = null;
const audioCtx = () =>
  (actx ??= new (window.AudioContext || (window as any).webkitAudioContext)());

/* -------------------- Audio Hooks API -------------------- */
interface AudioHooks {
  setBPM(bpm: number): void;
  countIn(atSec: number, beats: number): void;
  onWindowScheduled(perfectAtSec: number, railIndex: number): void;
  onPause(): void;
  onResumeAlignedToPerfect(perfectAtSec: number, railIndex: number): void;
  onSwitch(
    prevRailIndex: number,
    nextRailIndex: number,
    perfectAtSec: number
  ): void;
}
class DefaultMetronome implements AudioHooks {
  private bpm = BPM;
  setBPM(bpm: number) {
    this.bpm = bpm;
  }
  countIn(atSec: number, beats: number) {
    for (let i = 0; i < beats; i++)
      this.click(atSec + i * (60 / this.bpm), i === 0);
  }
  onWindowScheduled(perfectAtSec: number) {
    this.click(perfectAtSec, true);
  }
  onResumeAlignedToPerfect(perfectAtSec: number) {
    this.click(perfectAtSec, true);
  }
  onSwitch(_p: number, _n: number, perfectAtSec: number) {
    this.click(perfectAtSec, true);
  }
  onPause() {}
  private click(atTimeSec: number, accent = false) {
    const ctx = audioCtx();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "square";
    o.frequency.setValueAtTime(accent ? 1600 : 1150, atTimeSec);
    g.gain.setValueAtTime(0.0001, atTimeSec);
    g.gain.exponentialRampToValueAtTime(
      accent ? 0.24 : 0.18,
      atTimeSec + 0.004
    );
    g.gain.exponentialRampToValueAtTime(0.0001, atTimeSec + 0.06);
    o.connect(g).connect(ctx.destination);
    o.start(atTimeSec);
    o.stop(atTimeSec + 0.08);
  }
}
const audioHooks: AudioHooks = new DefaultMetronome();

function perfMsToAudioTime(targetMs: number): number {
  const ctx = audioCtx();
  return ctx.currentTime + (targetMs - performance.now()) / 1000;
}

/* -------------------- Shared utils -------------------- */
let CH = 12;
function measureCH(sampleEl: HTMLElement) {
  const probe = document.createElement("span");
  probe.className = "ch";
  probe.textContent = "M";
  sampleEl.appendChild(probe);
  CH = probe.getBoundingClientRect().width || 12;
  probe.remove();
}
function setFeedback(s: string) {
  feedbackEl.textContent = s;
  if (s) setTimeout(() => (feedbackEl.textContent = ""), 160);
}
function playTone(grade: Grade) {
  const ctx = audioCtx(),
    t = ctx.currentTime;
  const cfg = {
    perfect: { f: 880, d: 0.1 },
    great: { f: 740, d: 0.11 },
    good: { f: 580, d: 0.12 },
    poor: { f: 520, d: 0.1 },
    miss: { f: 320, d: 0.1 },
  }[grade];
  const o = ctx.createOscillator(),
    g = ctx.createGain();
  o.type = "sine";
  o.frequency.value = cfg.f;
  g.gain.setValueAtTime(0.0001, t);
  g.gain.linearRampToValueAtTime(0.16, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + cfg.d);
  o.connect(g).connect(ctx.destination);
  o.start(t);
  o.stop(t + cfg.d + 0.03);
}
function visualBoxBounds() {
  const t = trackEl.getBoundingClientRect(),
    g = gateBoxEl.getBoundingClientRect();
  const left = g.left - t.left,
    right = g.right - t.left,
    width = right - left,
    center = left + width / 2,
    half = width / 2;
  return { left, right, width, center, half };
}
function logicalBandBounds() {
  const raw = visualBoxBounds();
  const left = raw.left - LOGICAL_EXPAND_CH_LEFT * CH,
    right = raw.right + LOGICAL_EXPAND_CH_RIGHT * CH;
  const width = right - left,
    center = left + width / 2,
    half = width / 2;
  return { left, right, width, center, half };
}
function spatialGradeAtX(x: number): Grade {
  const vb = visualBoxBounds(),
    lb = logicalBandBounds();
  if (x < lb.left || x > lb.right) return "miss";
  if (x >= vb.left && x <= vb.right) {
    const frac = Math.abs(x - vb.center) / vb.half;
    if (frac <= BOX_PERFECT_FRAC) return "perfect";
    if (frac <= BOX_GREAT_FRAC) return "great";
    return "good";
  }
  return "poor";
}
function lcpLen(a: string, b: string) {
  const n = Math.min(a.length, b.length);
  let i = 0;
  while (i < n && a[i] === b[i]) i++;
  return i;
}

/* -------------------- Per-rail -------------------- */
type WordDom = {
  root: HTMLSpanElement;
  letters: HTMLSpanElement[]; // [space?] + glyphs
  hasLeadingSpace: boolean;
  text: string; // word text (no space)
};

class Rail {
  railRoot: HTMLDivElement;
  lineEl: HTMLDivElement;
  flyEl: HTMLDivElement;

  wordsDom: WordDom[] = [];
  charIndexInWord = 0; // absolute index into first word letters[] (may point to leading space)
  hadMissThisWord = false;

  baseLeftPx = 0;
  lineTX = 0;

  windowStartMs: number | null = null;
  startX = 0;
  velocityPxPerMs = 0;
  tStopMs = 0;
  atLeftStopThisWindow = false;
  pausedDueToLeftStop = false;

  inputLocked = false;
  earlyLatchActive = false;
  missLatchActive = false;
  bufferedGrade: Grade | null = null;

  ghostedEl: HTMLElement | null = null;

  constructor(public railIndex: number) {
    this.railRoot = document.createElement("div");
    this.railRoot.className = "rail-row";
    this.railRoot.style.position = "relative";
    this.railRoot.style.overflow = "hidden";

    this.lineEl = document.createElement("div");
    this.lineEl.className = "line";
    this.lineEl.style.position = "relative";
    this.lineEl.style.display = "inline-flex";
    this.lineEl.style.alignItems = "center";
    this.lineEl.style.gap = `${WORD_GAP_CH}ch`;
    this.lineEl.style.willChange = "transform";

    this.flyEl = document.createElement("div");
    this.flyEl.className = "fly";
    this.flyEl.style.position = "absolute";
    this.flyEl.style.top = "50%";
    this.flyEl.style.transform = "translateY(-50%)";
    this.flyEl.style.willChange = "left";
    this.flyEl.style.pointerEvents = "none";

    this.railRoot.appendChild(this.lineEl);
    this.railRoot.appendChild(this.flyEl);
    railsEl.appendChild(this.railRoot);

    measureCH(this.lineEl);
    this.buildInitialLine();
    this.relayoutAndAlign();

    this.windowStartMs = null;
    this.flyEl.textContent = "";
  }

  /* ---------- Build / layout ---------- */
  buildInitialLine() {
    this.lineEl.innerHTML = "";
    this.wordsDom = [];
    for (let i = 0; i < WORDS_VISIBLE; i++) {
      const text = pickWord();
      const wd = this.createWordDom(text, i !== 0);
      if (i === 0) wd.root.classList.add("active");
      this.wordsDom.push(wd);
      this.lineEl.appendChild(wd.root);
    }
    this.charIndexInWord = 0;
    this.hadMissThisWord = false;
    this.ensureFirstWordSpaceHidden();
  }

  createWordDom(text: string, withLeadingSpace: boolean): WordDom {
    const ws = document.createElement("span");
    ws.className = "word";
    const letters: HTMLSpanElement[] = [];

    if (withLeadingSpace) {
      const sp = document.createElement("span");
      sp.className = "ch space";
      sp.textContent = "·";
      letters.push(sp);
      ws.appendChild(sp);
    }
    for (let i = 0; i < text.length; i++) {
      const ch = document.createElement("span");
      ch.className = "ch";
      ch.textContent = text[i];
      letters.push(ch);
      ws.appendChild(ch);
    }
    return { root: ws, letters, hasLeadingSpace: withLeadingSpace, text };
  }

  /* ---------- Space handling (visual only; still matchable) ---------- */
  ensureFirstWordSpaceHidden() {
    const w0 = this.wordsDom[0];
    if (!w0) return;
    const letters = w0.letters;
    if (letters[0]?.classList.contains("space")) {
      letters[0].classList.add("hidden");
    }
  }

  /* ---------- PRISTINE reset of first word visuals ---------- */
  restoreToPristineFirstWord() {
    const w0 = this.wordsDom[0];
    if (!w0) return;
    const letters = w0.letters;
    for (let i = 0; i < letters.length; i++) {
      const el = letters[i];
      if (!el) continue;
      // keep leading space hidden; unhide all other glyphs
      if (!el.classList.contains("space")) el.classList.remove("hidden");
      el.classList.remove(
        "ghost",
        "switch-hint",
        "match-progress",
        "ident-progress"
      );
      el.style.fontStyle = "";
      el.style.fontWeight = "";
      el.style.textDecoration = "";
      el.style.textUnderlineOffset = "";
      el.style.textDecorationThickness = "";
    }
    const base = this.firstWordGlyphIndex();
    this.charIndexInWord = base;
    this.ensureFirstWordSpaceHidden();
    this.relayoutAndAlign();
  }

  /* ---------- Indexing ---------- */
  firstWordGlyphIndex(): number {
    return this.wordsDom[0].letters[0]?.classList.contains("space") ? 1 : 0;
  }
  spanAtWordGlyph(i: number): HTMLSpanElement | null {
    const base = this.firstWordGlyphIndex();
    return this.wordsDom[0].letters[base + i] ?? null;
  }
  wordGlyphCount(): number {
    const letters = this.wordsDom[0]?.letters ?? [];
    const base = this.firstWordGlyphIndex();
    return Math.max(0, letters.length - base);
  }
  consumedWordGlyphs(): number {
    const base = this.firstWordGlyphIndex();
    return Math.max(0, this.charIndexInWord - base);
  }
  currentWordTextLower(): string {
    return this.wordsDom[0].text.toLowerCase();
  }

  currentCharSpan(): HTMLSpanElement {
    return this.wordsDom[0].letters[this.charIndexInWord];
  }
  nextCharSpan(): HTMLSpanElement | null {
    const curr = this.wordsDom[0];
    if (this.charIndexInWord + 1 < curr.letters.length)
      return curr.letters[this.charIndexInWord + 1];
    const next = this.wordsDom[1];
    return next ? next.letters[0] : null;
  }
  firstPendingLetter(): string {
    const idx = this.firstWordGlyphIndex();
    const ch = this.wordsDom[0].letters[idx]?.textContent ?? "";
    return (ch || "").toLowerCase();
  }

  /* ---------- Hints / progress ---------- */
  clearAllHints() {
    const w = this.wordsDom[0];
    if (!w) return;
    for (const el of w.letters) {
      el.classList.remove("switch-hint", "match-progress", "ident-progress");
      el.style.fontStyle = "";
      el.style.fontWeight = "";
      el.style.textDecoration = "";
      el.style.textUnderlineOffset = "";
      el.style.textDecorationThickness = "";
    }
  }
  applyMatchProgress(n: number, kind: "soft" | "ident") {
    const base = this.firstWordGlyphIndex();
    const total = this.wordGlyphCount();
    const k = Math.max(0, Math.min(n, total));
    for (let i = 0; i < k; i++) {
      const el = this.wordsDom[0].letters[base + i];
      if (!el) break;
      el.classList.add(kind === "soft" ? "match-progress" : "ident-progress");
    }
  }
  setNextGlyphHintAt(idx: number) {
    const el = this.spanAtWordGlyph(idx);
    if (!el) return;
    el.classList.add("switch-hint");
    el.style.fontStyle = "italic";
    el.style.fontWeight = "700";
    el.style.textDecoration = "underline";
    el.style.textUnderlineOffset = "0.15em";
    el.style.textDecorationThickness = "2px";
  }

  /* ---------- Geometry / preview ---------- */
  charCenterXInLine(chEl: HTMLElement): number {
    const ch = chEl.getBoundingClientRect();
    const ln = this.lineEl.getBoundingClientRect();
    return ch.left - ln.left + ch.width / 2;
  }
  captureBaseLeft() {
    const t = trackEl.getBoundingClientRect();
    const l = this.lineEl.getBoundingClientRect();
    this.baseLeftPx = l.left - t.left - this.lineTX;
  }
  updatePreviewPositionOnce() {
    this.ensureFirstWordSpaceHidden();
    const { center } = logicalBandBounds();
    const ref = this.nextCharSpan() ?? this.currentCharSpan();
    const nextXInLine = this.charCenterXInLine(ref);
    const targetX = center + NEXT_OFFSET_CH * CH;
    const desiredVisualLeft = targetX - nextXInLine;
    const desiredTX = desiredVisualLeft - this.baseLeftPx;
    if (Math.abs(desiredTX - this.lineTX) > 0.5) {
      this.lineTX = desiredTX;
      this.lineEl.style.transform = `translateX(${this.lineTX}px)`;
    }
  }
  relayoutAndAlign() {
    measureCH(this.lineEl);
    this.captureBaseLeft();
    this.updatePreviewPositionOnce();
  }

  /* ---------- Ghost ---------- */
  clearGhost() {
    if (this.ghostedEl && !this.ghostedEl.classList.contains("hidden"))
      this.ghostedEl.classList.remove("ghost");
    this.ghostedEl = null;
  }
  ghostCurrentCharForWindow() {
    this.clearGhost();
    const el = this.currentCharSpan();
    if (!el.classList.contains("hidden")) {
      el.classList.add("ghost");
      this.ghostedEl = el;
    }
  }

  /* ---------- Consumption / restore ---------- */
  forceConsumeWordGlyphs(n: number) {
    this.ensureFirstWordSpaceHidden();
    const letters = this.wordsDom[0].letters;
    const base = this.firstWordGlyphIndex();
    const total = this.wordGlyphCount();
    const k = Math.min(n, total);
    for (let i = 0; i < k; i++) {
      const el = letters[base + i];
      if (el && !el.classList.contains("hidden")) el.classList.add("hidden");
    }
    this.charIndexInWord = Math.max(this.charIndexInWord, base + k);
  }
  rewindWordGlyphs(n: number) {
    if (n <= 0) return;
    const letters = this.wordsDom[0].letters;
    const base = this.firstWordGlyphIndex();
    const already = Math.max(0, this.charIndexInWord - base);
    const k = Math.min(n, already);
    for (let i = 1; i <= k; i++) {
      const idx = this.charIndexInWord - i;
      const el = letters[idx];
      if (!el) continue;
      if (el.classList.contains("hidden")) el.classList.remove("hidden");
    }
    this.charIndexInWord -= k;
    if (this.charIndexInWord < base) this.charIndexInWord = base;
    this.ensureFirstWordSpaceHidden();
    this.relayoutAndAlign();
  }
  restoreAllConsumedWordGlyphs() {
    this.ensureFirstWordSpaceHidden();
    const letters = this.wordsDom[0].letters;
    const base = this.firstWordGlyphIndex();
    const consumed = Math.max(0, this.charIndexInWord - base);
    for (let i = 0; i < consumed; i++) {
      const el = letters[base + i];
      if (el && el.classList.contains("hidden")) el.classList.remove("hidden");
    }
    this.charIndexInWord = base;
    this.ensureFirstWordSpaceHidden();
    this.relayoutAndAlign();
  }

  cancelAllLatches() {
    this.earlyLatchActive = false;
    this.missLatchActive = false;
    this.bufferedGrade = null;
    this.inputLocked = false;
    this.clearGhost();
    this.flyEl.textContent = "";
  }

  forceConsumeWholeWord() {
    // scrub first to avoid ghost classes surviving rotation
    this.restoreToPristineFirstWord();
    // hide all glyphs of the current (now-pristine) word to grant full credit
    const letters = this.wordsDom[0].letters;
    for (let i = 0; i < letters.length; i++)
      if (!letters[i].classList.contains("hidden"))
        letters[i].classList.add("hidden");
    // rotate queue
    const first = this.wordsDom.shift()!;
    first.root.remove();
    if (this.wordsDom[0]) this.wordsDom[0].root.classList.add("active");
    const newText = pickWord();
    const newWd = this.createWordDom(newText, true);
    this.wordsDom.push(newWd);
    this.lineEl.appendChild(newWd.root);
    this.charIndexInWord = 0;
    this.hadMissThisWord = false;
    this.ensureFirstWordSpaceHidden();
    this.relayoutAndAlign();
  }

  /* ---------- Window loop ---------- */
  startWindow(anchorStartMs?: number, syncToNow = false) {
    this.updatePreviewPositionOnce();
    const ch = this.currentCharSpan();
    this.flyEl.textContent = ch?.textContent || "";
    this.ghostCurrentCharForWindow();

    const fromX = this.baseLeftPx + this.lineTX + this.charCenterXInLine(ch);
    const { center: logicalCenter } = logicalBandBounds();
    const { left: visualLeft } = visualBoxBounds();

    this.startX = fromX;
    this.velocityPxPerMs = (logicalCenter - this.startX) / DWELL_MS;

    const leftStopX = visualLeft - STOP_MARGIN_CH * CH;
    const totalDistToStop = leftStopX - this.startX;
    this.tStopMs = totalDistToStop / this.velocityPxPerMs;

    this.windowStartMs = anchorStartMs ?? performance.now();
    this.atLeftStopThisWindow = false;

    this.earlyLatchActive = false;
    this.missLatchActive = false;
    this.bufferedGrade = null;
    this.inputLocked = false;

    const perfectMs = this.windowStartMs + DWELL_MS;
    audioHooks.onWindowScheduled(perfMsToAudioTime(perfectMs), this.railIndex);

    if (syncToNow) {
      const tMs = Math.max(0, performance.now() - this.windowStartMs);
      this.flyEl.style.left = `${this.flyXAt(tMs)}px`;
    } else {
      this.flyEl.style.left = `${this.startX}px`;
    }
  }

  stopWindow() {
    this.windowStartMs = null;
    this.cancelAllLatches();
    // NOTE: do not clear hints here; Manager re-applies every frame
  }

  flyXAt(tMs: number) {
    const t = Math.max(0, Math.min(tMs, this.tStopMs));
    return this.startX + this.velocityPxPerMs * t;
  }

  advanceChar(consumedWasSpace: boolean) {
    const el = this.currentCharSpan();
    el.classList.add("hidden");
    if (this.ghostedEl === el) this.ghostedEl = null;

    const active = this.wordsDom[0];
    this.charIndexInWord++;
    const finishedWord = this.charIndexInWord >= active.letters.length;

    if (consumedWasSpace) manager.onSpaceConsumed(this);

    if (finishedWord) {
      const finishedText = active.text;
      if (!this.hadMissThisWord) {
        // mirror identical words on other rails; strong rotate (scrub + rotate)
        manager.rails.forEach((r) => {
          if (r === this) return;
          if (r.wordsDom[0]?.text === finishedText) r.forceConsumeWholeWord();
        });
      }

      // rotate self
      const first = this.wordsDom.shift()!;
      first.root.remove();
      if (this.wordsDom[0]) this.wordsDom[0].root.classList.add("active");
      const newText = pickWord();
      const newWd = this.createWordDom(newText, true);
      this.wordsDom.push(newWd);
      this.lineEl.appendChild(newWd.root);
      this.charIndexInWord = 0;
      this.hadMissThisWord = false;
      this.ensureFirstWordSpaceHidden();
      this.relayoutAndAlign();
    }

    if (manager.activeRail === this) this.startWindow();
  }

  tick(now: number) {
    if (this.windowStartMs == null) return;
    const tMs = now - this.windowStartMs;
    const x = this.flyXAt(tMs);
    this.flyEl.style.left = `${x}px`;

    if (!this.atLeftStopThisWindow && tMs >= this.tStopMs) {
      this.atLeftStopThisWindow = true;
      this.pausedDueToLeftStop = true;
      if (manager.activeRail === this) audioHooks.onPause();
    }

    if (this.earlyLatchActive && tMs >= DWELL_MS) {
      const g = this.bufferedGrade ?? "perfect";
      setFeedback(g);
      playTone(g);
      this.earlyLatchActive = false;
      this.bufferedGrade = null;
      this.inputLocked = false;
      const wasSpace = this.currentCharSpan().classList.contains("space");
      this.advanceChar(wasSpace);
    }

    if (this.missLatchActive && tMs >= DWELL_MS) {
      setFeedback("miss");
      playTone("miss");
      this.missLatchActive = false;
      this.inputLocked = false;
      this.hadMissThisWord = true;
      const wasSpace = this.currentCharSpan().classList.contains("space");
      this.advanceChar(wasSpace);
    }
  }

  handleKey(key: string): boolean {
    if (manager.activeRail !== this) return false;
    if (this.inputLocked || this.windowStartMs == null) return false;
    if (key.length !== 1) return false;

    const el = this.currentCharSpan();
    const isSpaceMarker = el.classList.contains("space");
    const expected = isSpaceMarker ? " " : (el.textContent || "").toLowerCase();
    const normKey = key === " " ? " " : key.toLowerCase();
    const tMs = performance.now() - (this.windowStartMs || 0);

    if (manager.switchArmed && normKey !== expected) return false;

    if (normKey === expected) {
      if (tMs < DWELL_MS) {
        const xNow = this.flyXAt(tMs);
        this.bufferedGrade = spatialGradeAtX(xNow);
        this.earlyLatchActive = true;
        this.inputLocked = true;
        return true;
      }
      const xNow = this.flyXAt(tMs);
      const grade = spatialGradeAtX(xNow);
      setFeedback(grade);
      playTone(grade);
      this.advanceChar(isSpaceMarker);
      return true;
    } else {
      if (manager.trySoftSwitchFromMiss(this, normKey)) return true;

      if (tMs < DWELL_MS) {
        this.missLatchActive = true;
        this.inputLocked = true;
        this.hadMissThisWord = true;
        return true;
      }
      setFeedback("miss");
      playTone("miss");
      this.hadMissThisWord = true;
      this.advanceChar(isSpaceMarker);
      return true;
    }
  }
}

/* -------------------- Manager -------------------- */
class RailManager {
  rails: Rail[] = [];
  activeRail!: Rail;

  switchArmed = false;
  private pivotMinOverlap = 0; // prevents switch-back to weaker candidates

  rafId: number | null = null;

  constructor() {
    for (let i = 0; i < RAIL_COUNT; i++) this.rails.push(new Rail(i));
    this.activeRail = this.rails[0];

    this.ensureGateSize();
    this.moveGateToActive(false);

    audioHooks.setBPM(BPM);

    const ctx = audioCtx();
    const t0 = ctx.currentTime + 0.08;
    audioHooks.countIn(t0, 2);
    const firstAudio = t0 + 2 * (60 / BPM);
    const delayMs = (firstAudio - ctx.currentTime) * 1000;

    setTimeout(() => {
      this.activeRail.startWindow();
      if (this.rafId) cancelAnimationFrame(this.rafId);
      const loop = () => {
        const now = performance.now();
        this.activeRail.tick(now);
        // pivot increases with actual progress
        const typed = this.activeRail.consumedWordGlyphs();
        if (typed > this.pivotMinOverlap) this.pivotMinOverlap = typed;
        this.updateHints(); // frame-driven, prevents stale classes
        this.rafId = requestAnimationFrame(loop);
      };
      this.rafId = requestAnimationFrame(loop);
    }, Math.max(0, delayMs));
  }

  /* ---- Gate ---- */
  ensureGateSize() {
    const row0 = this.rails[0]?.railRoot;
    if (!row0) return;
    const rowH = row0.offsetHeight;
    gateBoxEl.style.width = `${GATE_W_CH * CH}px`;
    gateBoxEl.style.height = `${rowH}px`;
    gateBoxEl.style.position = "absolute";
    gateBoxEl.style.left = gateBoxEl.style.left || "50%";
  }
  moveGateToActive(animate: boolean) {
    this.ensureGateSize();
    const targetTop = this.activeRail.railRoot.offsetTop;
    gateBoxEl.style.transition = animate ? "top 140ms ease" : "none";
    gateBoxEl.style.top = `${targetTop}px`;
  }

  /* ---- Hints (recomputed each frame) ---- */
  private updateHints() {
    // clear first
    this.rails.forEach((r) => r.clearAllHints());

    if (this.switchArmed) {
      // hard-switch hints: underline first glyph of all rails
      this.rails.forEach((r) => r.setNextGlyphHintAt(0));
      return;
    }

    // soft candidates
    const active = this.activeRail;
    const typedCount = active.consumedWordGlyphs();
    if (typedCount <= 0) return;

    const typedPrefix = active.currentWordTextLower().slice(0, typedCount);
    for (const r of this.rails) {
      if (r === active) continue;

      const cand = r.currentWordTextLower();

      // identical word: show ident progress; never eligible for soft-switch
      if (cand === active.currentWordTextLower()) {
        r.applyMatchProgress(typedCount, "ident");
        continue;
      }

      const L = lcpLen(cand, typedPrefix);
      if (L < this.pivotMinOverlap) continue; // pivot guard (prevents switch-back)
      if (L > 0) {
        r.applyMatchProgress(L, "soft");
        if (L < cand.length) r.setNextGlyphHintAt(L);
      }
    }
  }

  onSpaceConsumed(rail: Rail) {
    if (rail === this.activeRail) {
      this.setSwitchArmed(true);
      this.pivotMinOverlap = 0; // new epoch on hard-choice arming
    }
  }
  private setSwitchArmed(on: boolean) {
    this.switchArmed = on;
  }

  /* ---- Miss-triggered soft switch with pivot guard ---- */
  trySoftSwitchFromMiss(prev: Rail, wrongKey: string): boolean {
    if (this.switchArmed) return false;

    const typedCount = prev.consumedWordGlyphs();
    if (typedCount <= 0) return false;

    const typedPrefix = prev.currentWordTextLower().slice(0, typedCount);

    let best: { target: Rail; overlap: number } | null = null;
    for (const r of this.rails) {
      if (r === prev) continue;
      const cand = r.currentWordTextLower();
      if (cand === prev.currentWordTextLower()) continue; // never switch to identical word
      const L = lcpLen(cand, typedPrefix);
      if (L < this.pivotMinOverlap) continue; // pivot guard
      if (L <= 0) continue;
      if (L < cand.length && cand[L] !== wrongKey) continue; // wrong key must continue candidate
      if (
        !best ||
        L > best.overlap ||
        (L === best.overlap && r.railIndex < best.target.railIndex)
      ) {
        best = { target: r, overlap: L };
      }
    }
    if (!best) return false;

    const { target, overlap } = best;
    const anchor = prev.windowStartMs ?? performance.now();

    // PRISTINE RESTORE of the previous rail before switching
    prev.cancelAllLatches();
    prev.restoreToPristineFirstWord(); // stronger than rewind/restore subset
    prev.relayoutAndAlign();

    // Retro-credit target for the overlapped prefix (letters only)
    target.forceConsumeWordGlyphs(overlap);
    target.relayoutAndAlign();

    // Phase-preserving switch
    const prevIdx = prev.railIndex;
    this.setActiveRail(target, {
      anchorStartMs: anchor,
      prevIndex: prevIdx,
      minOverlapAtSwitch: overlap,
    });

    // Deliver the wrong key on the new active rail
    target.handleKey(wrongKey);

    return true;
  }

  handleKey(e: KeyboardEvent) {
    if (!actx) audioCtx();
    const key =
      e.key.length === 1 ? (e.key === " " ? " " : e.key.toLowerCase()) : "";
    if (!key) return;

    if (this.switchArmed) {
      const stay = this.activeRail.firstPendingLetter() === key;
      if (stay) {
        this.setSwitchArmed(false);
        this.pivotMinOverlap = 0;
        this.activeRail.handleKey(key);
        return;
      }
      const target = this.rails.find(
        (r) => r !== this.activeRail && r.firstPendingLetter() === key
      );
      if (target) {
        const anchor = this.activeRail.windowStartMs ?? performance.now();
        const prevIdx = this.activeRail.railIndex;
        this.setSwitchArmed(false);
        this.setActiveRail(target, {
          anchorStartMs: anchor,
          prevIndex: prevIdx,
          minOverlapAtSwitch: 0,
        });
        target.handleKey(key);
        return;
      }
      return;
    }

    this.activeRail.handleKey(key);
  }

  setActiveRail(
    rail: Rail,
    opts?: {
      anchorStartMs?: number;
      prevIndex?: number;
      minOverlapAtSwitch?: number;
    }
  ) {
    if (this.activeRail === rail) return;

    const prev = this.activeRail;
    prev.stopWindow();
    prev.relayoutAndAlign();

    this.activeRail = rail;
    this.moveGateToActive(true);

    const anchor = opts?.anchorStartMs ?? performance.now();
    this.activeRail.startWindow(anchor, true);

    const newPerfectMs =
      (this.activeRail.windowStartMs ?? performance.now()) + DWELL_MS;
    audioHooks.onSwitch(
      opts?.prevIndex ?? prev.railIndex,
      this.activeRail.railIndex,
      perfMsToAudioTime(newPerfectMs)
    );

    if (this.activeRail.pausedDueToLeftStop) {
      audioHooks.onResumeAlignedToPerfect(
        perfMsToAudioTime(newPerfectMs),
        this.activeRail.railIndex
      );
      this.activeRail.pausedDueToLeftStop = false;
    }

    // Seed/Reset pivot for new active
    this.pivotMinOverlap = Math.max(0, opts?.minOverlapAtSwitch ?? 0);
  }
}

/* -------------------- Boot & Resize -------------------- */
const manager = new RailManager();
document.addEventListener("keydown", (e) => manager.handleKey(e));
document.addEventListener(
  "click",
  () => {
    if (!actx) audioCtx();
  },
  { once: true }
);

let resizeRAF: number | null = null;
window.addEventListener("resize", () => {
  if (resizeRAF) cancelAnimationFrame(resizeRAF);
  resizeRAF = requestAnimationFrame(() => {
    manager.rails.forEach((r) => {
      r.ensureFirstWordSpaceHidden();
      r.relayoutAndAlign();
    });
    manager.ensureGateSize();
    manager.moveGateToActive(false);
  }) as unknown as number;
});

/* -------------------- Optional CSS helpers --------------------
.match-progress { opacity:.65; }
.ident-progress { opacity:.5; text-decoration: underline dotted currentColor; text-underline-offset:.15em; }
.switch-hint { font-style:italic; font-weight:700; text-decoration:underline; text-underline-offset:.15em; text-decoration-thickness:2px; }
.space { opacity:.35; }
.hidden { visibility:hidden; }
.ghost { opacity:.3; }
---------------------------------------------------------------- */
