// src/svc/clock.ts
import { useGameStore } from "../state";

export const SECONDS_PER_NIGHT = 36 * 60;
export const SECONDS_PER_NIGHTSTORM = 10;
export const HOURS_PER_NIGHT = 20;

export const BASE_NIGHTYEAR = 200;
export const SECONDS_PER_DAY = 86400;
const EPOCH = new Date(Date.UTC(2025, 11, 1, 5, 0, 0));

const _cycles = SECONDS_PER_DAY / SECONDS_PER_NIGHT;
if (Math.abs(_cycles - Math.round(_cycles)) > 1e-9) {
  throw new Error(`got ${_cycles} cycles per real day.`);
}

export const NIGHTS_PER_DAY = Math.round(_cycles);
export const SECONDS_PER_NIGHT_HOUR = SECONDS_PER_NIGHT / HOURS_PER_NIGHT;

export class NightClock {
  readonly dt: Date;

  constructor(dt?: Date) {
    if (dt) {
      this.dt = new Date(dt);
    } else {
      const { getServerNow } = useGameStore.getState();
      this.dt = getServerNow();
    }
  }

  private get _realMonthStart(): Date {
    const year = this.dt.getFullYear();
    const month = this.dt.getMonth(); // 0-based
    return new Date(year, month, 1, 0, 0, 0, 0);
  }

  private get _nextRealMonthStart(): Date {
    const year = this.dt.getFullYear();
    const month = this.dt.getMonth();
    if (month === 11) {
      return new Date(year + 1, 0, 1, 0, 0, 0, 0);
    } else {
      return new Date(year, month + 1, 1, 0, 0, 0, 0);
    }
  }

  private get _secondsSinceDtMidnight(): number {
    const year = this.dt.getFullYear();
    const month = this.dt.getMonth();
    const day = this.dt.getDate();
    const midnight = new Date(year, month, day, 0, 0, 0, 0);
    return (this.dt.getTime() - midnight.getTime()) / 1000;
  }

  get nightsSinceDtMidnight(): number {
    return Math.floor(this._secondsSinceDtMidnight / SECONDS_PER_NIGHT);
  }

  get nightyears(): number {
    const year = this.dt.getFullYear();
    const monthIndex = this.dt.getMonth();
    const monthsSinceEpoch = (year - 2025) * 12 + (monthIndex - 11);
    return BASE_NIGHTYEAR + monthsSinceEpoch;
  }

  get moons(): number {
    return this.dt.getDate();
  }

  get elapsedPct(): number {
    const sec = this.seconds;
    return sec / SECONDS_PER_NIGHT;
  }

  get hours(): number {
    const hourIndex = Math.floor(this.elapsedPct * HOURS_PER_NIGHT * 60) / 60;
    let hour24 = 6 + Math.floor(hourIndex); // 6->25
    if (hour24 >= 24) hour24 -= 24;
    return hour24;
  }

  get hoursFloat(): number {
    const totalNightMinutes = this.elapsedPct * HOURS_PER_NIGHT * 60.0;
    const hourOffset = totalNightMinutes / 60.0; // 0..20
    let h = 6.0 + hourOffset; // 6..26
    if (h >= 24.0) h -= 24.0;
    return h;
  }

  get minutes(): number {
    return Math.floor(this.elapsedPct * HOURS_PER_NIGHT * 60) % 60;
  }

  get seconds(): number {
    const s = this._secondsSinceDtMidnight % SECONDS_PER_NIGHT;
    return s < 0 ? s + SECONDS_PER_NIGHT : s;
  }

  get nextHourEta(): number {
    const hoursElapsed = Math.floor(this.seconds / SECONDS_PER_NIGHT_HOUR);
    const next = (hoursElapsed + 1) * SECONDS_PER_NIGHT_HOUR;
    let eta = next - this.seconds;
    eta = Math.max(0, Math.min(eta, SECONDS_PER_NIGHT - this.seconds));
    return eta;
  }

  get secondsRemaining(): number {
    return SECONDS_PER_NIGHT - this.seconds;
  }

  get nightyearElapsedPct(): number {
    const start = this._realMonthStart;
    const end = this._nextRealMonthStart;
    const dur = (end.getTime() - start.getTime()) / 1000;
    if (dur <= 0) return 0;
    const elapsed = (this.dt.getTime() - start.getTime()) / 1000;
    return elapsed / dur;
  }

  get dawn(): number {
    const s = this.nightyearElapsedPct;
    const angle = 2 * Math.PI * s;

    const avgDaylen = 13.25;
    const ampDaylen = 2.75;

    const avgCenter = 13.125;
    const ampCenter = 0.875;

    const daylen = avgDaylen - ampDaylen * Math.cos(angle);
    const center = avgCenter - ampCenter * Math.cos(angle);

    const sunrise = center - daylen / 2.0;
    return Math.max(0.0, Math.min(24.0, sunrise));
  }

  get dusk(): number {
    const s = this.nightyearElapsedPct;
    const angle = 2 * Math.PI * s;

    const avgDaylen = 13.25;
    const ampDaylen = 2.75;

    const avgCenter = 13.125;
    const ampCenter = 0.875;

    const daylen = avgDaylen - ampDaylen * Math.cos(angle);
    const center = avgCenter - ampCenter * Math.cos(angle);

    const sunset = center + daylen / 2.0;
    return Math.max(0.0, Math.min(24.0, sunset));
  }

  get inNightstorm(): boolean {
    const remaining = SECONDS_PER_NIGHT - this.seconds;
    return remaining <= SECONDS_PER_NIGHTSTORM && SECONDS_PER_NIGHTSTORM > 0;
  }

  get nightstormEta(): number {
    const startT = SECONDS_PER_NIGHT - SECONDS_PER_NIGHTSTORM;
    return startT - this.seconds;
  }

  get nightstormElapsedPct(): number {
    if (!this.inNightstorm) return 0.0;
    const remaining = SECONDS_PER_NIGHT - this.seconds;
    return 1.0 - remaining / SECONDS_PER_NIGHTSTORM;
  }

  // -------------------------
  // Epoch, days, nights
  // -------------------------

  get secondsSinceEpoch(): number {
    return Math.max(0, (this.dt.getTime() - EPOCH.getTime()) / 1000);
  }

  get moonsSinceEpoch(): number {
    return Math.floor(this.secondsSinceEpoch / SECONDS_PER_DAY);
  }

  get nightsSinceEpoch(): number {
    return this.moonsSinceEpoch * NIGHTS_PER_DAY + this.nightsSinceDtMidnight;
  }

  get nightsThisNightyear(): number {
    const start = this._realMonthStart;
    const secondsSinceEpochAtStart = (start.getTime() - EPOCH.getTime()) / 1000;
    const moonsSinceStart = Math.floor(
      secondsSinceEpochAtStart / SECONDS_PER_DAY
    );
    const cyclesBeforeYearStart = moonsSinceStart * NIGHTS_PER_DAY;
    const current = this.nightsSinceEpoch;
    return Math.max(0, current - cyclesBeforeYearStart);
  }

  get brightnessIndex(): number {
    if (this.inNightstorm) return 0;

    const h = this.hoursFloat; // 0..24
    const sunrise = this.dawn;
    const sunset = this.dusk;

    let brightnessNorm: number;

    if (sunrise <= h && h <= sunset) {
      let t = (h - sunrise) / (sunset - sunrise);
      t = Math.max(0, Math.min(1, t));
      brightnessNorm = 0.5 + 0.5 * Math.sin(Math.PI * t);
    } else {
      const d = h < sunrise ? 24.0 - sunset + h : h - sunset;
      const dMax = 6.0;
      const falloff = Math.max(0.0, 1.0 - d / dMax);
      brightnessNorm = 0.5 * falloff;
    }

    const band = 1 + Math.round(6 * brightnessNorm);
    return Math.max(1, Math.min(7, band));
  }
}
