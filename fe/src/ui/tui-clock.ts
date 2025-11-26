// src/ui/tui-clock.ts
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { NightClock } from "../svc/clock";
import { sharedStyles } from "./tui-styles";

type IconSeverity = 0 | 1 | 2 | 3;

type ClockSnapshot = {
  nightyear: number;
  hour: number;
  minutes: number;
  brightness: number; // 0–7 (0 = nightstorm)
  inNightstorm: boolean;
  nightstormEta: number; // seconds until nightstorm start (<= 0 means in storm)
  seasonLabel: string; // e.g. "WINTER", "SUMMER ✶"
};

@customElement("tui-clock")
export class TuiClock extends LitElement {
  @state() private snap: ClockSnapshot | null = null;
  private _timer: number | null = null;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: inline-block;
        font-size: 16px;
        font-weight: 300;
        line-height: 1.1;
        --clock-icon-wght: 400;
      }

      .clock-line {
        display: inline-flex;
      }

      .line-wrap {
        display: inline-flex;
        align-items: center;
        gap: 1ch;
      }

      .icon-wrap {
        display: inline-flex;
        align-items: center;
      }

      .icon {
        font-family: "Material Symbols Rounded";
        font-size: 18px;
        color: var(--c-high);
        font-variation-settings: "FILL" 1, "GRAD" 0, "opsz" 20,
          "wght" var(--clock-icon-wght, 400);
      }

      /* --- Text color wiring --- */
      .season,
      .time {
        color: var(--c-mid);
      }

      .year,
      .bullet {
        color: var(--c-low);
      }

      .colon {
        color: var(--c-low);
        animation: colon-blink 3s steps(2, start) infinite;
      }

      /* --- Animation tiers --- */

      /* 0: calm */
      .icon-wrap[data-severity="0"] .icon {
        opacity: 0.9;
      }

      .icon-wrap[data-severity="1"] .icon {
        animation: pulse-soft 4s ease-in-out infinite;
      }

      .icon-wrap[data-severity="2"] .icon {
        animation: pulse-medium 1.6s ease-in-out infinite;
      }

      .icon-wrap[data-severity="3"] .icon {
        color: var(--c-high);
        animation: siren 0.22s steps(2, end) infinite;
      }

      @keyframes pulse-soft {
        0%,
        100% {
          opacity: 0.9;
        }
        50% {
          opacity: 1;
        }
      }

      @keyframes pulse-medium {
        0%,
        100% {
          transform: scale(1);
          opacity: 0.8;
        }
        50% {
          transform: scale(1.02);
          opacity: 1;
        }
      }

      @keyframes colon-blink {
        0%,
        49% {
          opacity: 1;
        }
        50%,
        100% {
          opacity: 0.1;
        }
      }

      @keyframes siren {
        0% {
          transform: scale(1);
          opacity: 0.4;
        }
        25% {
          transform: scale(1.12);
          opacity: 1;
        }
        50% {
          transform: scale(0.98);
          opacity: 0.3;
        }
        75% {
          transform: scale(1.08);
          opacity: 1;
        }
        100% {
          transform: scale(1);
          opacity: 0.5;
        }
      }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    this._tick();
    this._timer = window.setInterval(() => this._tick(), 1000);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._timer !== null) {
      window.clearInterval(this._timer);
      this._timer = null;
    }
  }

  private _tick(): void {
    const nc = new NightClock();
    const seasonLabel = this.seasonLabel(nc);
    const minutes = Math.floor(nc.minutes / 5) * 5; // bucket to 5-minute steps

    const snap: ClockSnapshot = {
      nightyear: nc.nightyears,
      hour: nc.hours,
      minutes,
      brightness: nc.brightnessIndex,
      inNightstorm: nc.inNightstorm,
      nightstormEta: nc.nightstormEta,
      seasonLabel,
    };

    this.snap = snap;

    const wght = this.iconWeight(snap);
    this.style.setProperty("--clock-icon-wght", String(wght));
  }

  private seasonLabel(nc: NightClock): string {
    const s = nc.nightyearElapsedPct; // 0..1
    const seasons = ["WINTER", "SPRING", "SUMMER", "AUTUMN"] as const;
    const idx = Math.floor(s * 4) % 4;
    return seasons[idx];
  }

  // Icon name for Material Symbols
  private iconName(s: ClockSnapshot): string {
    if (s.inNightstorm || s.brightness === 0) {
      return "cyclone";
    }
    // brightness_1 .. brightness_7
    const b = Math.max(1, Math.min(7, s.brightness));
    return `brightness_${b}`;
  }

  private iconWeight(s: ClockSnapshot): number {
    if (s.inNightstorm || s.brightness === 0) {
      return 400;
    }
    const b = Math.max(1, Math.min(7, s.brightness));
    const base = 200;
    const step = (700 - base) / 6.0;
    return Math.round(base + (b - 1) * step);
  }

  private iconSeverity(s: ClockSnapshot): IconSeverity {
    const eta = s.nightstormEta;

    // Already in nightstorm: full siren
    if (eta <= 10) return 3;

    // Seconds until storm: closer → hotter
    if (eta <= 60) return 2; // last 15s before storm
    if (eta <= 120) return 1; // last minute before storm
    return 0; // otherwise calm
  }

  protected render() {
    if (!this.snap) return html``;

    const { seasonLabel, nightyear, hour, minutes, brightness } = this.snap;
    const h = hour.toString().padStart(2, "0");
    const m = minutes.toString().padStart(2, "0");
    const icon = this.iconName(this.snap);
    const severity = this.iconSeverity(this.snap);

    //prettier-ignore
    return html`
      <span class="clock-line">
        <span class="line-wrap">
          <span class="season text-layer">${seasonLabel}</span>
          <span class="text-layer"><span class="year">Y</span>${nightyear}</span>
          <span class="bullet text-layer">•</span>
          <span class="time text-layer">
            <span class="hh">${h}</span
            ><span class="colon">:</span
            ><span class="mm">${m}</span>
          </span>
          <span class="icon-wrap" data-severity=${severity}>
            <span class="icon" data-b=${brightness}>${icon}</span>
          </span>
        </span>
      </span>
    `;
  }
}
