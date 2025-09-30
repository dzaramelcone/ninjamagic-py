// rail.ts — Stationary preview (exactly 3 words), left gate BOX, jitter-free alignment.
// Multi-rail beat typing with: (1) proper gate size/placement,
// (2) only-active-rail motion, (3) deterministic switching after space.
// Fixes: flyer/preview misalignment after adding words. We now (1) re-measure and
// recapture base-left after any DOM change, and (2) ALWAYS realign the preview
// BEFORE computing the flyer’s start position for a window. This removes the “flyer
// starts to the left of the box” glitch.
//
// Features (per requirements):
// - Preview shows exactly THREE words (active + 2 next). When a word finishes,
//   it is removed and a new one is appended immediately (stays at 3).
// - Larger spacing between words (WORD_GAP_CH).
// - NEXT_OFFSET_CH = 6 (pin NEXT pending letter ~6ch to right of box center).
// - Spatial rating depends ONLY on symmetric distance from box center:
//     * Inside the visible box: at least GOOD (near center PERFECT, then GREAT, then GOOD).
//     * Between box edge and logical band edge: POOR.
//     * Outside logical band: MISS.
//   There is no "late" rating.
// - Analytic motion: constant velocity so the flyer hits the logical center exactly
//   at one beat (DWELL_MS = 60000/BPM). It then continues to a stop left of the box.
// - Spaces must be typed: words after the active word show a space marker "·" and
//   require the spacebar (" ") first.
//
// Adjust the visual box in rail.html; logic here uses a wider logical band than the
// visual box for friendliness, with modest left bias for “late” forgiveness.

type Grade = "perfect" | "great" | "good" | "poor" | "miss";

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

const RAIL_COUNT = 3; // exactly 3 rails
const GATE_W_CH = 2.5; // visual box width in ch; JS will set px based on measured CH

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

const trackEl = document.getElementById("track") as HTMLDivElement;
const railsEl = document.getElementById("rails") as HTMLDivElement;
const gateBoxEl = document.getElementById("gateBox") as HTMLDivElement;
const feedbackEl = document.getElementById("feedback") as HTMLDivElement;

// --- Audio / metronome (global, only matters for active rail) ---
let actx: AudioContext | null = null;
const audio = () =>
  (actx ??= new (window.AudioContext || (window as any).webkitAudioContext)());

let metroNextTime = 0;
let metroInterval = 60 / BPM;
let beatCount = 0;
let metroStarted = false;

function scheduleClick(atTimeSec: number, accent = false) {
  const ctx = audio();
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = "square";
  o.frequency.setValueAtTime(accent ? 1600 : 1150, atTimeSec);
  g.gain.setValueAtTime(0.0001, atTimeSec);
  g.gain.exponentialRampToValueAtTime(accent ? 0.25 : 0.18, atTimeSec + 0.003);
  g.gain.exponentialRampToValueAtTime(0.0001, atTimeSec + 0.06);
  o.connect(g).connect(ctx.destination);
  o.start(atTimeSec);
  o.stop(atTimeSec + 0.08);
}
function pauseMetronome() {
  metroStarted = false;
}
function resumeMetronomeAlignedToPerfect() {
  const ctx = audio();
  metroInterval = 60 / BPM;
  metroNextTime = ctx.currentTime + DWELL_MS / 1000;
  beatCount = 0;
  metroStarted = true;
}
function tickMetronome() {
  if (!metroStarted || !actx) return;
  const ahead = 0.1,
    now = actx.currentTime;
  while (metroNextTime < now + ahead) {
    scheduleClick(metroNextTime, beatCount % 4 === 0);
    metroNextTime += metroInterval;
    beatCount++;
  }
}

// --- Shared utils ---
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
  if (s) setTimeout(() => (feedbackEl.textContent = ""), 200);
}
function playTone(grade: Grade) {
  const ctx = audio();
  const t = ctx.currentTime;
  const cfg = {
    perfect: { f: 880, d: 0.1 },
    great: { f: 740, d: 0.11 },
    good: { f: 580, d: 0.12 },
    poor: { f: 520, d: 0.1 },
    miss: { f: 320, d: 0.1 },
  }[grade];
  const o = ctx.createOscillator();
  const g = ctx.createGain();
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
  const t = trackEl.getBoundingClientRect();
  const g = gateBoxEl.getBoundingClientRect();
  const left = g.left - t.left,
    right = g.right - t.left;
  const width = right - left,
    center = left + width / 2,
    half = width / 2;
  return { left, right, width, center, half };
}
function logicalBandBounds() {
  const raw = visualBoxBounds();
  const left = raw.left - LOGICAL_EXPAND_CH_LEFT * CH;
  const right = raw.right + LOGICAL_EXPAND_CH_RIGHT * CH;
  const width = right - left,
    center = left + width / 2,
    half = width / 2;
  return { left, right, width, center, half };
}
function spatialGradeAtX(x: number): Grade {
  const vb = visualBoxBounds();
  const lb = logicalBandBounds();
  if (x < lb.left || x > lb.right) return "miss";
  if (x >= vb.left && x <= vb.right) {
    const frac = Math.abs(x - vb.center) / vb.half;
    if (frac <= BOX_PERFECT_FRAC) return "perfect";
    if (frac <= BOX_GREAT_FRAC) return "great";
    return "good";
  }
  return "poor";
}

// --- Per-rail ---
type WordDom = {
  root: HTMLSpanElement;
  letters: HTMLSpanElement[];
  hasLeadingSpace: boolean;
  text: string;
};

class Rail {
  railRoot: HTMLDivElement;
  lineEl: HTMLDivElement;
  flyEl: HTMLDivElement;

  wordsDom: WordDom[] = [];
  charIndexInWord = 0;

  baseLeftPx = 0;
  lineTX = 0;

  // Motion state (only meaningful for the active rail)
  windowStartMs: number | null = null;
  startX = 0;
  velocityPxPerMs = 0;
  tStopMs = 0;
  atLeftStopThisWindow = false;
  pausedDueToLeftStop = false;

  // Latches
  inputLocked = false;
  earlyLatchActive = false;
  missLatchActive = false;
  bufferedGrade: Grade | null = null;

  ghostedEl: HTMLElement | null = null;

  constructor(public railIndex: number) {
    this.railRoot = document.createElement("div");
    this.railRoot.className = "rail-row";

    this.lineEl = document.createElement("div");
    this.lineEl.className = "line";
    this.lineEl.style.gap = `${WORD_GAP_CH}ch`;

    this.flyEl = document.createElement("div");
    this.flyEl.className = "fly";
    this.flyEl.style.position = "absolute";
    this.flyEl.style.top = "50%";
    this.flyEl.style.transform = "translateY(-50%)";
    this.flyEl.style.willChange = "left";

    this.railRoot.appendChild(this.lineEl);
    this.railRoot.appendChild(this.flyEl);
    railsEl.appendChild(this.railRoot);

    measureCH(this.lineEl);
    this.buildInitialLine();
    this.relayoutAndAlign();

    // Inactive by default (only index 0 starts moving later)
    this.windowStartMs = null;
    this.flyEl.textContent = "";
  }

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

  currentCharSpan(): HTMLSpanElement {
    return this.wordsDom[0].letters[this.charIndexInWord];
  }
  nextCharSpan(): HTMLSpanElement | null {
    const curr = this.wordsDom[0];
    if (this.charIndexInWord + 1 < curr.letters.length)
      return curr.letters[this.charIndexInWord + 1];
    const nextWord = this.wordsDom[1];
    return nextWord ? nextWord.letters[0] : null;
  }

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

  clearGhost() {
    if (this.ghostedEl && !this.ghostedEl.classList.contains("hidden")) {
      this.ghostedEl.classList.remove("ghost");
    }
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

  // Start motion ONLY for the active rail
  startWindow(anchorStartMs?: number, syncToNow: boolean = false) {
    this.updatePreviewPositionOnce();

    const ch = this.currentCharSpan();
    this.flyEl.textContent = ch.textContent || "";
    this.ghostCurrentCharForWindow();

    const fromX = this.baseLeftPx + this.lineTX + this.charCenterXInLine(ch);
    const { center: logicalCenter } = logicalBandBounds();
    const { left: visualLeft } = visualBoxBounds();

    this.startX = fromX;
    this.velocityPxPerMs = (logicalCenter - this.startX) / DWELL_MS;

    const leftStopX = visualLeft - STOP_MARGIN_CH * CH;
    const totalDistToStop = leftStopX - this.startX;
    this.tStopMs = totalDistToStop / this.velocityPxPerMs;

    // >>> NEW: keep the same phase if an anchor is provided
    this.windowStartMs = anchorStartMs ?? performance.now();

    this.atLeftStopThisWindow = false;
    this.earlyLatchActive = false;
    this.missLatchActive = false;
    this.bufferedGrade = null;
    this.inputLocked = false;

    // If we’re syncing into an already-running phase, place the flyer accordingly
    if (syncToNow) {
      const tMs = Math.max(0, performance.now() - this.windowStartMs);
      this.flyEl.style.left = `${this.flyXAt(tMs)}px`;
    } else {
      this.flyEl.style.left = `${this.startX}px`;
    }
  }
  // Stop motion (used when leaving active rail)
  stopWindow() {
    this.windowStartMs = null;
    this.earlyLatchActive = false;
    this.missLatchActive = false;
    this.bufferedGrade = null;
    this.inputLocked = false;
    this.flyEl.textContent = "";
  }

  flyXAt(tMs: number): number {
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

    if (consumedWasSpace) {
      // Inform manager deterministically that the space was consumed.
      manager.onSpaceConsumed(this);
    }

    if (finishedWord) {
      // rotate
      const first = this.wordsDom.shift()!;
      first.root.remove();
      this.wordsDom[0].root.classList.add("active");

      const newText = pickWord();
      const newWd = this.createWordDom(newText, true);
      this.wordsDom.push(newWd);
      this.lineEl.appendChild(newWd.root);
      this.charIndexInWord = 0;

      this.relayoutAndAlign();
    }

    // Only the active rail runs motion
    if (manager.activeRail === this) this.startWindow();
  }

  tick(now: number) {
    if (this.windowStartMs == null) return; // inactive rails don't move
    const tMs = now - this.windowStartMs;
    const x = this.flyXAt(tMs);
    this.flyEl.style.left = `${x}px`;

    if (!this.atLeftStopThisWindow && tMs >= this.tStopMs) {
      this.atLeftStopThisWindow = true;
      this.pausedDueToLeftStop = true;
      if (manager.activeRail === this) pauseMetronome();
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
      const wasSpace = this.currentCharSpan().classList.contains("space");
      this.advanceChar(wasSpace);
    }
  }

  // Returns true if consumed.
  handleKey(key: string): boolean {
    // Only active rail accepts keys (switch logic handled by manager)
    if (manager.activeRail !== this) return false;
    if (this.inputLocked || this.windowStartMs == null) return false;
    if (key.length !== 1) return false;

    const el = this.currentCharSpan();
    const isSpaceMarker = el.classList.contains("space");
    const expected = isSpaceMarker ? " " : (el.textContent || "").toLowerCase();
    const normKey = key === " " ? " " : key.toLowerCase();

    const tMs = performance.now() - (this.windowStartMs || 0);

    if (normKey === expected) {
      if (tMs < DWELL_MS) {
        const xNow = this.flyXAt(tMs);
        this.bufferedGrade = spatialGradeAtX(xNow); // capture grade-at-press
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
      if (tMs < DWELL_MS) {
        this.missLatchActive = true;
        this.inputLocked = true;
        return true;
      }
      // Late wrong → immediate miss & advance
      setFeedback("miss");
      playTone("miss");
      this.advanceChar(isSpaceMarker);
      return true;
    }
  }

  firstPendingLetter(): string {
    const letters = this.wordsDom[0].letters;
    let idx = 0;
    if (letters[0]?.classList.contains("space")) idx = 1;
    const ch = letters[idx]?.textContent ?? "";
    return (ch || "").toLowerCase();
  }

  isAtSpace(): boolean {
    const el = this.currentCharSpan();
    return !!el?.classList.contains("space");
  }
}

// --- Manager ---
class RailManager {
  rails: Rail[] = [];
  activeRail!: Rail;
  switchArmed = false;
  rafId: number | null = null;

  constructor() {
    // Build exactly 3 rails and append to DOM
    for (let i = 0; i < RAIL_COUNT; i++) this.rails.push(new Rail(i));
    this.activeRail = this.rails[0];

    // Gate: size & position AFTER rails exist
    this.ensureGateSize();
    this.moveGateToActive(false);

    // Count-in + start ONLY the active rail
    const ctx = audio();
    const t0 = ctx.currentTime + 0.08;
    metroInterval = 60 / BPM;
    metroNextTime = t0;
    beatCount = 0;
    metroStarted = true;
    for (let i = 0; i < 2; i++) scheduleClick(t0 + i * metroInterval, i === 0);

    const firstAudio = t0 + 2 * metroInterval;
    const delayMs = (firstAudio - ctx.currentTime) * 1000;
    setTimeout(() => {
      this.activeRail.startWindow();
      if (this.rafId) cancelAnimationFrame(this.rafId);
      const loop = () => {
        const now = performance.now();
        this.activeRail.tick(now); // only active rail moves
        tickMetronome();
        this.rafId = requestAnimationFrame(loop);
      };
      this.rafId = requestAnimationFrame(loop);
    }, Math.max(0, delayMs));
  }

  private ensureGateSize() {
    const row0 = this.rails[0]?.railRoot;
    if (!row0) return;
    const rowH = row0.offsetHeight;
    gateBoxEl.style.width = `${GATE_W_CH * CH}px`;
    gateBoxEl.style.height = `${rowH}px`;
  }

  // Called deterministically when a space was consumed on some rail
  onSpaceConsumed(rail: Rail) {
    if (rail === this.activeRail) {
      this.switchArmed = true;
    }
  }

  handleKey(e: KeyboardEvent) {
    if (!actx) audio();
    const key =
      e.key.length === 1 ? (e.key === " " ? " " : e.key.toLowerCase()) : "";
    if (!key) return;

    // If switching is armed, decide routing FIRST (don’t let the active rail consume it)
    if (this.switchArmed) {
      const stayOnActive = this.activeRail.firstPendingLetter() === key;
      if (stayOnActive) {
        this.switchArmed = false;
        this.activeRail.handleKey(key);
        return;
      }
      const target = this.rails.find(
        (r) => r !== this.activeRail && r.firstPendingLetter() === key
      );
      if (target) {
        this.switchArmed = false;
        // >>> NEW: preserve the phase from the current rail
        const old = this.activeRail;
        this.setActiveRail(target, { inheritPhaseFrom: old });
        target.handleKey(key); // deliver the same key on the same phase
        return;
      }
      // No rail matches: ignore key, keep switch armed
      return;
    }

    // Normal flow
    this.activeRail.handleKey(key);
  }

  setActiveRail(rail: Rail, opts?: { inheritPhaseFrom?: Rail }) {
    if (this.activeRail === rail) return;

    // Keep the old anchor (the phase we must preserve)
    const anchor =
      opts?.inheritPhaseFrom?.windowStartMs ??
      this.activeRail.windowStartMs ??
      performance.now();

    // Stop old active rail’s motion
    this.activeRail.stopWindow();

    // Switch
    this.activeRail = rail;
    this.moveGateToActive(true);

    // If the new active had paused at left-stop, resume metronome aligned
    if (rail.pausedDueToLeftStop) {
      resumeMetronomeAlignedToPerfect();
      rail.pausedDueToLeftStop = false;
    }

    // >>> NEW: start the new rail using the SAME anchor (same perfect time)
    this.activeRail.startWindow(anchor, /*syncToNow*/ true);
  }

  private moveGateToActive(animate: boolean) {
    this.ensureGateSize(); // make sure width/height are correct first
    const targetTop = this.activeRail.railRoot.offsetTop;
    gateBoxEl.style.transition = animate ? "top 140ms ease" : "none";
    gateBoxEl.style.top = `${targetTop}px`;
  }
}

// Global instance (declared before Rails use it)
let manager: RailManager;
manager = new RailManager();

// Global key handling
document.addEventListener("keydown", (e) => manager.handleKey(e));

// Kick audio on first click
document.addEventListener(
  "click",
  () => {
    if (!actx) audio();
  },
  { once: true }
);

// Resize: reflow alignment, gate size/position
let resizeRAF: number | null = null;
window.addEventListener("resize", () => {
  if (resizeRAF) cancelAnimationFrame(resizeRAF);
  resizeRAF = requestAnimationFrame(() => {
    manager.rails.forEach((r) => r.relayoutAndAlign());
    manager["ensureGateSize"](); // call the private via bracket or make it public
    manager["moveGateToActive"](false); // same note as above
  }) as unknown as number;
});
