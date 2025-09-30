// rail.ts — Stationary preview (exactly 3 words), left gate BOX, jitter-free alignment.
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
const DWELL_MS = 60000 / BPM; // one beat per letter window

const NEXT_OFFSET_CH = 6; // pin NEXT pending letter this far to the right of box center
const WORDS_VISIBLE = 3; // always exactly 3 words visible
const WORD_GAP_CH = 1.4; // larger spacing between words

// Logical vs visual gate tuning (logical band is wider/more forgiving).
const LOGICAL_EXPAND_CH_LEFT = 0.9; // forgiveness to the left
const LOGICAL_EXPAND_CH_RIGHT = 0.9; // a bit to the right as well
const STOP_MARGIN_CH = 0.6; // flyer stop left of the *visual* box

// Grading thresholds inside the visible box (fractions of half-width from center).
const BOX_PERFECT_FRAC = 0.4; // ≤40% → perfect
const BOX_GREAT_FRAC = 0.8; // ≤80% → great
// between visible box edge and logical band edge → POOR; outside logical band → MISS.
// --- Lexicon (medieval flavor) ---
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

const trackEl = document.getElementById("track") as HTMLDivElement;
const gateBoxEl = document.getElementById("gateBox") as HTMLDivElement; // visual box
const lineEl = document.getElementById("line") as HTMLDivElement;
const flyEl = document.getElementById("fly") as HTMLDivElement;
const feedbackEl = document.getElementById("feedback") as HTMLDivElement;

// audio / metronome
let actx: AudioContext | null = null;
const audio = () =>
  (actx ??= new (window.AudioContext || (window as any).webkitAudioContext)());

function pickWord() {
  return LEXICON[Math.floor(Math.random() * LEXICON.length)];
}

type WordDom = {
  root: HTMLSpanElement; // .word container
  letters: HTMLSpanElement[]; // includes leading space marker for non-active words
  hasLeadingSpace: boolean;
  text: string; // word text (no space)
};

let wordsDom: WordDom[] = []; // exactly 3 items
let charIndexInWord = 0; // index inside active word's letters (0..len-1)

function createWordDom(text: string, withLeadingSpace: boolean): WordDom {
  const ws = document.createElement("span");
  ws.className = "word";
  const letters: HTMLSpanElement[] = [];

  if (withLeadingSpace) {
    const sp = document.createElement("span");
    sp.className = "ch space"; // visual marker for required space
    sp.textContent = "·"; // expected key is " "
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

// Build initial 3-word line
function buildInitialLine() {
  lineEl.innerHTML = "";
  lineEl.style.gap = `${WORD_GAP_CH}ch`; // enlarge word spacing

  wordsDom = [];
  for (let i = 0; i < WORDS_VISIBLE; i++) {
    const text = pickWord();
    const wd = createWordDom(text, i !== 0); // words after the first have a leading space marker
    if (i === 0) wd.root.classList.add("active");
    wordsDom.push(wd);
    lineEl.appendChild(wd.root);
  }
  charIndexInWord = 0;
}

// After finishing a word, remove it and append a new one (keeps 3 total)
function rotateWordsAfterWordFinish() {
  // Remove first word
  const first = wordsDom.shift()!;
  first.root.remove();

  // The new active word is the former index 1 (it ALREADY has a leading space marker)
  wordsDom[0].root.classList.add("active");

  // Append a brand new trailing word with a leading space marker
  const newText = pickWord();
  const newWd = createWordDom(newText, true);
  wordsDom.push(newWd);
  lineEl.appendChild(newWd.root);

  // Reset char index to 0 (we must type the leading space of the now-active word)
  charIndexInWord = 0;

  // IMPORTANT: After DOM changes, re-measure & re-capture base-left, then realign preview.
  relayoutAndAlign();
}

// ----- Geometry helpers (stable, transform-invariant math) -----

let CH = 12; // px per "ch"
let baseLeftPx = 0; // line's visual left when lineTX == 0
let lineTX = 0; // our applied translateX (we never read back CSS transforms)

function measureCH() {
  const probe = document.createElement("span");
  probe.className = "ch";
  probe.textContent = "M";
  lineEl.appendChild(probe);
  CH = probe.getBoundingClientRect().width || 12;
  probe.remove();
}

function captureBaseLeft() {
  const t = trackEl.getBoundingClientRect();
  const l = lineEl.getBoundingClientRect();
  // Record base-left in the current DOM state, removing our transform.
  baseLeftPx = l.left - t.left - lineTX;
}

function visualBoxBounds() {
  const t = trackEl.getBoundingClientRect();
  const g = gateBoxEl.getBoundingClientRect();
  const left = g.left - t.left;
  const right = g.right - t.left;
  const width = right - left;
  const center = left + width / 2;
  const half = width / 2;
  return { left, right, width, center, half };
}

function logicalBandBounds() {
  const raw = visualBoxBounds();
  const left = raw.left - LOGICAL_EXPAND_CH_LEFT * CH;
  const right = raw.right + LOGICAL_EXPAND_CH_RIGHT * CH;
  const width = right - left;
  const center = left + width / 2;
  const half = width / 2;
  return { left, right, width, center, half };
}

// Center x of a character (span) relative to the line's left (transform-invariant)
function charCenterXInLine(chEl: HTMLElement): number {
  const ch = chEl.getBoundingClientRect();
  const ln = lineEl.getBoundingClientRect();
  return ch.left - ln.left + ch.width / 2;
}

// Current/next character spans
function currentCharSpan(): HTMLSpanElement {
  return wordsDom[0].letters[charIndexInWord];
}
function nextCharSpan(): HTMLSpanElement | null {
  const curr = wordsDom[0];
  if (charIndexInWord + 1 < curr.letters.length)
    return curr.letters[charIndexInWord + 1];
  const nextWord = wordsDom[1];
  return nextWord ? nextWord.letters[0] : null;
}

// ----- Preview alignment (called after DOM changes and on each window start) -----

function updatePreviewPositionOnce() {
  // target: pin NEXT pending letter to logical center + NEXT_OFFSET_CH
  const { center } = logicalBandBounds();
  const ref = nextCharSpan() ?? currentCharSpan();
  const nextXInLine = charCenterXInLine(ref); // invariant to transform
  const targetX = center + NEXT_OFFSET_CH * CH;
  const desiredVisualLeft = targetX - nextXInLine;
  const desiredTX = desiredVisualLeft - baseLeftPx;
  if (Math.abs(desiredTX - lineTX) > 0.5) {
    lineTX = desiredTX;
    lineEl.style.transform = `translateX(${lineTX}px)`;
  }
}

// Convenience: after any DOM mutation to #line, call this to keep math stable
function relayoutAndAlign() {
  measureCH();
  captureBaseLeft(); // recalc baseLeft in the NEW DOM state
  updatePreviewPositionOnce();
}

// ----- Metronome (simple click each beat) -----

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

// ----- Feedback -----

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

// ----- Ghost the stationary copy during each window -----

let ghostedEl: HTMLElement | null = null;

function clearGhost() {
  if (ghostedEl && !ghostedEl.classList.contains("hidden")) {
    ghostedEl.classList.remove("ghost");
  }
  ghostedEl = null;
}
function ghostCurrentCharForWindow() {
  clearGhost();
  const el = currentCharSpan();
  if (!el.classList.contains("hidden")) {
    el.classList.add("ghost");
    ghostedEl = el;
  }
}

// ----- Analytic motion (reach logical center at exactly DWELL_MS) -----

let windowStartMs: number | null = null;
let startX = 0; // px
let velocityPxPerMs = 0; // computed so that x(t=DWELL_MS) == logicalCenter
let tStopMs = 0; // time when we reach the left stop (after crossing center)

function startWindow() {
  // IMPORTANT ORDER:
  // 1) Realign preview to the target (so lineTX is final for this window)
  // 2) THEN compute flyer startX using the final transform
  updatePreviewPositionOnce();

  const ch = currentCharSpan();
  flyEl.textContent = ch.textContent || "";
  ghostCurrentCharForWindow();

  // compute motion params AFTER alignment
  const fromX = baseLeftPx + lineTX + charCenterXInLine(ch);
  const { center: logicalCenter } = logicalBandBounds();
  const { left: visualLeft } = visualBoxBounds();

  startX = fromX;
  velocityPxPerMs = (logicalCenter - startX) / DWELL_MS;

  // left stop is to the left of the VISUAL box
  const leftStopX = visualLeft - STOP_MARGIN_CH * CH;
  const totalDistToStop = leftStopX - startX; // negative (moving left)
  tStopMs = totalDistToStop / velocityPxPerMs; // positive ms to reach left stop

  // init time & visuals
  windowStartMs = performance.now();
  flyEl.style.left = `${startX}px`;

  // reset stripes
  trackEl.style.backgroundPosition = "0 0";
}

// position at time t (ms since windowStart), clamped to stop
function flyXAt(tMs: number): number {
  const t = Math.max(0, Math.min(tMs, tStopMs));
  return startX + velocityPxPerMs * t;
}

// ----- Advance char / word -----

function advanceChar() {
  // permanently hide this char (keep width)
  const el = currentCharSpan();
  el.classList.add("hidden");
  if (ghostedEl === el) ghostedEl = null;

  const active = wordsDom[0];
  charIndexInWord++;

  // finished the active word?
  const finishedWord = charIndexInWord >= active.letters.length;

  if (finishedWord) {
    rotateWordsAfterWordFinish(); // also realigns preview & base-left
  }

  // Start next window (startWindow realigns again and picks correct flyer position)
  startWindow();
}

// ----- Spatial grading (symmetric) -----

function spatialGradeAtX(x: number): Grade {
  const vb = visualBoxBounds();
  const lb = logicalBandBounds();

  if (x < lb.left || x > lb.right) return "miss";

  if (x >= vb.left && x <= vb.right) {
    const frac = Math.abs(x - vb.center) / vb.half;
    if (frac <= BOX_PERFECT_FRAC) return "perfect";
    if (frac <= BOX_GREAT_FRAC) return "great";
    return "good"; // inside box but near edges
  }

  // Between visual box edge and logical band edge
  return "poor";
}

// ----- Main loop -----

let rafId: number | null = null;

function loop() {
  if (windowStartMs == null) return;
  const now = performance.now();
  const tMs = now - windowStartMs;

  // move flyer analytically
  const x = flyXAt(tMs);
  flyEl.style.left = `${x}px`;

  // sweep stripes based on normalized time to DWELL_MS (0..1..>1)
  const k = Math.min(1, Math.max(0, tMs / DWELL_MS));
  const shift = Math.floor(120 * k);
  trackEl.style.backgroundPosition = `-${shift}px 0`;

  tickMetronome();
  rafId = requestAnimationFrame(loop);
}

// ----- Start / Input / Resize -----

function setUpInitial() {
  lineEl.style.gap = `${WORD_GAP_CH}ch`;

  buildInitialLine();
  // After the initial DOM is in place, re-measure and align ONCE.
  measureCH();
  lineTX = 0;
  lineEl.style.transform = `translateX(0px)`;
  captureBaseLeft();
  updatePreviewPositionOnce(); // align immediately so first flyer starts from correct slot

  // metronome
  const ctx = audio();
  const t0 = ctx.currentTime + 0.08;
  metroInterval = 60 / BPM;
  metroNextTime = t0;
  beatCount = 0;
  metroStarted = true;
  for (let i = 0; i < 2; i++) scheduleClick(t0 + i * metroInterval, i === 0);

  // first window aligned just after count-in
  const firstAudio = t0 + 2 * metroInterval;
  const delayMs = (firstAudio - ctx.currentTime) * 1000;
  setTimeout(() => {
    startWindow();
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(loop);
  }, Math.max(0, delayMs));
}
function onKeydown(e: KeyboardEvent) {
  if (!actx) audio();
  if (!windowStartMs) {
    setUpInitial();
    return;
  }
  if (e.key.length !== 1) return;

  // Determine expected char
  const el = currentCharSpan();
  const isSpaceMarker = el.classList.contains("space");
  const expected = isSpaceMarker ? " " : (el.textContent || "").toLowerCase();
  const key = e.key === " " ? " " : e.key.toLowerCase();

  if (key === expected) {
    // Compute current flyer position analytically at this instant
    const tMs = performance.now() - (windowStartMs || 0);
    const x = flyXAt(tMs);

    const grade = spatialGradeAtX(x);
    setFeedback(grade);
    playTone(grade);

    // Always advance immediately on correct key
    advanceChar();
  } else {
    // WRONG KEY: force a miss and consume the letter (advance).
    setFeedback("miss");
    playTone("miss");
    advanceChar();
  }
}

document.addEventListener("keydown", onKeydown);

// Initial kick if the user clicks or presses any key to start audio context
document.addEventListener(
  "click",
  () => {
    if (!actx) audio();
  },
  { once: true }
);

// Keep alignment stable on resize (re-measure, recapture base-left, then realign)
let resizeRAF: number | null = null;
window.addEventListener("resize", () => {
  if (resizeRAF) cancelAnimationFrame(resizeRAF);
  resizeRAF = requestAnimationFrame(() => {
    relayoutAndAlign();
  }) as unknown as number;
});
