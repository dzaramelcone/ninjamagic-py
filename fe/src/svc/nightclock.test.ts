import { describe, expect, it, vi } from "vitest";

vi.mock("../state", () => ({
  useGameStore: {
    getState: () => ({
      getServerNow: () => new Date(),
    }),
  },
}));

import { EPOCH, NightClock, SECONDS_PER_NIGHT_ACTIVE } from "./nightclock";

function utcDate(
  year: number,
  month: number,
  day: number,
  hour = 0,
  minute = 0,
  second = 0
): Date {
  return new Date(Date.UTC(year, month - 1, day, hour, minute, second));
}

describe("NightClock UTC alignment", () => {
  it("treats input dates as UTC", () => {
    const dt = utcDate(2026, 7, 1, 0, 0, 0); // July 1, 00:00 UTC
    const clock = new NightClock(dt);

    expect(clock.seconds).toBe(0);
    expect(clock.hours).toBe(6);
    expect(clock.minutes).toBe(0);
  });

  it("resets nightsThisNightyear at real month boundaries", () => {
    const dt = utcDate(2026, 4, 1, 0, 0, 0); // April 1, 00:00 UTC
    const clock = new NightClock(dt);

    expect(clock.nightsThisNightyear).toBe(0);
  });

  it("enters nightstorm at active-night boundary", () => {
    const dt = new Date(EPOCH.getTime() + SECONDS_PER_NIGHT_ACTIVE * 1000);
    const clock = new NightClock(dt);

    expect(clock.inNightstorm).toBe(true);
    expect(clock.hours).toBe(2);
    expect(clock.minutes).toBe(0);
  });
});
