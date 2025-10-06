// Inline phrase stays fixed; next phrase is appended as a new line below.
// Metronome + tempo-locked letter dwell retained.

type Grade = "perfect" | "great" | "good" | "miss";

const BPM = 250;
const BEATS_PER_LETTER = 1;
const COUNT_IN_BEATS = 2;

const PHRASE_WORDS = 8; // words per line
const MIN_QUEUE_WORDS = 50; // keep plenty buffered

const LEXICON =
  "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua".split(
    " "
  );

const fieldEl = document.getElementById("word") as HTMLDivElement;
const feedbackEl = document.getElementById("feedback") as HTMLDivElement;

let actx: AudioContext | null = null;
const audio = () =>
  (actx ??= new (window.AudioContext || (window as any).webkitAudioContext)());

const msPerBeat = (bpm: number) => 60000 / bpm;
const DWELL_MS = msPerBeat(BPM) * BEATS_PER_LETTER;

// ---------- word/line state --------------------------------------------------

let queue: string[] = [];
let qPtr = 0; // pointer into queue for creating new lines

type Line = { words: string[]; el: HTMLDivElement };
let lines: Line[] = [];
let curLineIdx = 0; // which line is active
let curWordIdx = 0; // which word within line is active
let curLetterIdx = 0; // which letter within word is active

// ---------- timing state -----------------------------------------------------

let startedAt: number | null = null;
let letterStartAt: number | null = null;
let rafId: number | null = null;
let hitThisLetter = false;

// metronome
let metroNextTime = 0;
let metroInterval = 60 / BPM;
let metroStarted = false;
let beatCount = 0;

// ---------- helpers ----------------------------------------------------------

function chooseWord(): string {
  return LEXICON[Math.floor(Math.random() * LEXICON.length)];
}
function refillQueue(minWords: number) {
  while (queue.length - qPtr < minWords) queue.push(chooseWord());
}
function currentLine(): Line {
  return lines[curLineIdx];
}
function currentWord(): string {
  return currentLine().words[curWordIdx];
}

// Build a new line from the queue and append it below
function appendLine(): Line {
  refillQueue(PHRASE_WORDS);
  const words = queue.slice(qPtr, qPtr + PHRASE_WORDS);
  qPtr += PHRASE_WORDS;

  const el = document.createElement("div");
  el.className = "line";
  fieldEl.appendChild(el);

  const line = { words, el };
  lines.push(line);
  renderLine(line, /*injectCursor*/ false);
  return line;
}

// Render only the given line; inject the active cursor if this is the active line
function renderLine(line: Line, injectCursor: boolean) {
  const isActiveLine = line === currentLine();
  line.el.innerHTML = "";

  line.words.forEach((w, wIdx) => {
    const wordSpan = document.createElement("span");
    const activeWord = isActiveLine && wIdx === curWordIdx;
    wordSpan.className = "word" + (activeWord ? " active" : "");

    for (let i = 0; i < w.length; i++) {
      const chSpan = document.createElement("span");
      const isActiveCh = activeWord && i === curLetterIdx;
      chSpan.className = "ch" + (isActiveCh ? " active" : "");
      chSpan.textContent = w[i];

      if (injectCursor && isActiveCh) {
        const cursor = document.createElement("span");
        cursor.className = "cursor";
        cursor.style.left = "0px";
        chSpan.appendChild(cursor);
      }
      wordSpan.appendChild(chSpan);
    }

    line.el.appendChild(wordSpan);
  });
}

function drawCursor(phase: number) {
  const lineEl = currentLine().el;
  const activeCh = lineEl.querySelector(
    ".word.active .ch.active"
  ) as HTMLElement | null;
  if (!activeCh) return;
  const cursor = activeCh.querySelector(".cursor") as HTMLElement | null;
  if (!cursor) return;

  const w = activeCh.getBoundingClientRect().width || 1;
  const px = Math.max(0, Math.min(1, phase)) * w;
  cursor.style.left = `${px}px`;
}

// ---------- advancing --------------------------------------------------------

function advanceWord() {
  curWordIdx++;
  if (curWordIdx >= currentLine().words.length) {
    // finished this line; append a new one and move down without touching prior lines
    curLineIdx++;
    const nextLine = appendLine();
    curWordIdx = 0;
    curLetterIdx = 0;
    hitThisLetter = false;

    // re-render only the new active line with cursor
    renderLine(nextLine, true);
  } else {
    curLetterIdx = 0;
    hitThisLetter = false;
    renderLine(currentLine(), true);
  }
  letterStartAt = performance.now();
}

function advanceLetter() {
  curLetterIdx++;
  if (curLetterIdx >= currentWord().length) {
    advanceWord();
  } else {
    hitThisLetter = false;
    renderLine(currentLine(), true);
    letterStartAt = performance.now();
  }
}

// ---------- metronome --------------------------------------------------------

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
  const ahead = 0.1;
  const now = actx.currentTime;

  while (metroNextTime < now + ahead) {
    const accent = beatCount % BEATS_PER_LETTER === 0;
    scheduleClick(metroNextTime, accent);
    metroNextTime += metroInterval;
    beatCount++;
  }
}

// ---------- start & loop -----------------------------------------------------

function start() {
  // reset state
  queue = [];
  qPtr = 0;
  lines = [];
  curLineIdx = 0;
  curWordIdx = 0;
  curLetterIdx = 0;
  hitThisLetter = false;
  fieldEl.innerHTML = "";

  refillQueue(MIN_QUEUE_WORDS);

  // first line
  const firstLine = appendLine();
  renderLine(firstLine, true);

  // audio + metronome with count-in; align first letter to the beat grid
  const ctx = audio();
  const t0 = ctx.currentTime + 0.08;
  metroInterval = 60 / BPM;
  metroNextTime = t0;
  beatCount = 0;
  metroStarted = true;

  for (let i = 0; i < COUNT_IN_BEATS; i++) {
    scheduleClick(t0 + i * metroInterval, i === 0);
  }

  const firstLetterAudioTime = t0 + COUNT_IN_BEATS * metroInterval;
  const delayMs = (firstLetterAudioTime - ctx.currentTime) * 1000;
  letterStartAt = performance.now() + delayMs;

  startedAt = performance.now();
  if (rafId) cancelAnimationFrame(rafId);
  rafId = requestAnimationFrame(loop);
}

function loop() {
  if (!letterStartAt) return;
  const now = performance.now();
  const phase = (now - letterStartAt) / DWELL_MS;

  drawCursor(phase);
  tickMetronome();

  if (phase >= 1) {
    advanceLetter();
  }

  rafId = requestAnimationFrame(loop);
}

// ---------- feedback ---------------------------------------------------------

function setFeedback(grade: Grade | "") {
  feedbackEl.textContent = grade ? grade : "";
  if (grade) setTimeout(() => (feedbackEl.textContent = ""), 220);
}
function playTone(grade: Grade) {
  if (grade === "miss") return;
  const ctx = audio();
  const t = ctx.currentTime;
  const cfg = {
    perfect: { f: 880, d: 0.11 },
    great: { f: 740, d: 0.12 },
    good: { f: 580, d: 0.14 },
  }[grade];
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = "sine";
  o.frequency.value = cfg.f;
  g.gain.setValueAtTime(0.0001, t);
  g.gain.linearRampToValueAtTime(0.18, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + cfg.d);
  o.connect(g).connect(ctx.destination);
  o.start(t);
  o.stop(t + cfg.d + 0.03);
}
function gradeFromPhase(phase: number): Grade {
  if (phase < 0 || phase > 1) return "miss";
  const d = Math.abs(phase - 0.5);
  if (d <= 0.1) return "perfect";
  if (d <= 0.22) return "great";
  return "good";
}

// ---------- input ------------------------------------------------------------

function onKeydown(e: KeyboardEvent) {
  if (!letterStartAt) return;
  if (e.key.length !== 1) return;

  const expect = currentWord()[curLetterIdx];
  const key = e.key.toLowerCase();
  const phase = (performance.now() - letterStartAt) / DWELL_MS;

  if (!hitThisLetter && key === expect && phase >= 0 && phase <= 1) {
    hitThisLetter = true;
    const grade = gradeFromPhase(phase);
    setFeedback(grade);
    playTone(grade);
  } else if (key !== expect) {
    setFeedback("miss");
  }
}

document.addEventListener("keydown", (e) => {
  if (!actx) audio(); // gesture-unlock audio
  if (!startedAt) start();
  onKeydown(e);
});
