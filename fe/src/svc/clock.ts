// src/svc/clock.ts
import { useGameStore } from "../state";

export const SECONDS_PER_NIGHT = 36 * 60;
export const SECONDS_PER_NIGHTSTORM = 10;
export const HOURS_PER_NIGHT = 20;

export const BASE_NIGHTYEAR = 200;
export const SECONDS_PER_DAY = 86400;

export const EPOCH = new Date(Date.UTC(2025, 11, 1, 5, 0, 0));

const _cycles = SECONDS_PER_DAY / SECONDS_PER_NIGHT;
if (Math.abs(_cycles - Math.round(_cycles)) > 1e-9) {
  throw new Error(
    `SECONDS_PER_NIGHT=${SECONDS_PER_NIGHT} does not divide 86400 cleanly; got ${_cycles} cycles per real day.`
  );
}

export const NIGHTS_PER_DAY = Math.round(_cycles);
export const SECONDS_PER_NIGHT_HOUR = SECONDS_PER_NIGHT / HOURS_PER_NIGHT;

const EST_PARTS_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "numeric",
  second: "numeric",
  hour12: false,
});

type ESTParts = {
  year: number; // e.g. 2025
  month: number; // 1-12
  day: number; // 1-31
  hour: number; // 0-23
  minute: number; // 0-59
  second: number; // 0-59
};

function getESTParts(date: Date): ESTParts {
  const parts = EST_PARTS_FORMATTER.formatToParts(date);
  let year = 0,
    month = 0,
    day = 0,
    hour = 0,
    minute = 0,
    second = 0;

  for (const p of parts) {
    const v = Number(p.value);
    switch (p.type) {
      case "year":
        year = v;
        break;
      case "month":
        month = v;
        break;
      case "day":
        day = v;
        break;
      case "hour":
        hour = v;
        break;
      case "minute":
        minute = v;
        break;
      case "second":
        second = v;
        break;
    }
  }
  return { year, month, day, hour, minute, second };
}

function daysInMonth(year: number, month1Based: number): number {
  return new Date(Date.UTC(year, month1Based, 0)).getUTCDate();
}

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

  private get _secondsSinceDtMidnight(): number {
    const { hour, minute, second } = getESTParts(this.dt);
    return hour * 3600 + minute * 60 + second;
  }

  get nightsSinceDtMidnight(): number {
    return Math.floor(this._secondsSinceDtMidnight / SECONDS_PER_NIGHT);
  }

  get elapsedPct(): number {
    const sec = this.seconds;
    return sec / SECONDS_PER_NIGHT;
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

  // Nightyear / calendar

  get nightyears(): number {
    const { year, month } = getESTParts(this.dt);
    const monthsSinceEpoch = (year - 2025) * 12 + (month - 12);
    return BASE_NIGHTYEAR + monthsSinceEpoch;
  }

  get moons(): number {
    const { day } = getESTParts(this.dt);
    return day;
  }

  get nightyearElapsedPct(): number {
    const { year, month, day, hour, minute, second } = getESTParts(this.dt);
    const dim = daysInMonth(year, month); // month is 1..12

    const secondsSinceMonthStart =
      (day - 1) * SECONDS_PER_DAY + hour * 3600 + minute * 60 + second;

    return secondsSinceMonthStart / (dim * SECONDS_PER_DAY);
  }

  get hours(): number {
    const hourIndex = Math.floor(this.elapsedPct * HOURS_PER_NIGHT * 60) / 60;
    let hour24 = 6 + Math.floor(hourIndex); // 6 -> 25
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

  get dawn(): number {
    const s = this.nightyearElapsedPct; // 0..1
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
    const { year, month } = getESTParts(this.dt);
    const startYear = year;
    const startMonth = month; // 1..12

    const startParts = {
      year: startYear,
      month: startMonth,
      day: 1,
      hour: 0,
      minute: 0,
      second: 0,
    };

    const monthsSinceEpoch =
      (startParts.year - 2025) * 12 + (startParts.month - 12);
    const secondsSinceEpochAtStartMonth =
      monthsSinceEpoch * 30 * SECONDS_PER_DAY; // approximate; structure only

    const moonsSinceStart = Math.floor(
      secondsSinceEpochAtStartMonth / SECONDS_PER_DAY
    );
    const cyclesBeforeYearStart = moonsSinceStart * NIGHTS_PER_DAY;
    const current = this.nightsSinceEpoch;
    return Math.max(0, current - cyclesBeforeYearStart);
  }

  get brightnessIndex(): number {
    if (this.inNightstorm) return 0;

    const h = this.hoursFloat; // 0..24
    const sunrise = this.dawn; // between ~6 and 7
    const sunset = this.dusk; // between ~17.5 and 22

    let brightnessNorm: number;

    if (sunrise <= h && h <= sunset) {
      let t = (h - sunrise) / (sunset - sunrise);
      t = Math.max(0, Math.min(1, t));
      brightnessNorm = 0.5 + 0.5 * Math.sin(Math.PI * t);
    } else {
      const d = h < sunrise ? 24.0 - sunset + h : h - sunset;
      const dMax = 6.0;
      const falloff = Math.max(0.0, 1.0 - d / dMax);
      brightnessNorm = 0.5 * falloff; // 0..0.5
    }

    const band = 1 + Math.round(6 * brightnessNorm);
    return Math.max(1, Math.min(7, band));
  }
}
