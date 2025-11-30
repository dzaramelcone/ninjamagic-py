"""Stateless, injective mapping from real-world timestamp to game time."""

import math
from datetime import datetime, timedelta, timezone

EST = timezone(timedelta(hours=-5), name="EST")


# CONFIGURABLE WORLD CONSTANTS
SECONDS_PER_NIGHTSTORM: float = 10.0
# 18m or 36m in seconds; must divide 86400
SECONDS_PER_NIGHT: float = 18.0 * 60.0
HOURS_PER_NIGHT: int = 20  # 06:00 -> 02:00

BASE_NIGHTYEAR: int = 200
EPOCH = datetime(2025, 12, 1, 0, 0, 0, tzinfo=EST)

SECONDS_PER_DAY = 86400.0

# validate divisibility
_cycles = SECONDS_PER_DAY / SECONDS_PER_NIGHT
if abs(_cycles - round(_cycles)) > 1e-9:
    raise ValueError(
        f"SECONDS_PER_NIGHT={SECONDS_PER_NIGHT} does not divide 86400 cleanly; "
        f"got {_cycles} cycles per real day."
    )
NIGHTS_PER_DAY: int = int(round(_cycles))

# length of one in-game hour in real seconds
SECONDS_PER_NIGHT_HOUR: float = SECONDS_PER_NIGHT / HOURS_PER_NIGHT


def now():
    return datetime.now(tz=EST)


class NightClock:
    """Stateless, injective mapping from real-world EST timestamp to game time."""

    def __init__(self, dt: datetime | None = None):
        if not dt:
            dt = datetime.now(EST)
        dt = dt.astimezone(EST) if dt.tzinfo else dt.replace(tzinfo=EST)
        self.dt = dt

    @property
    def _real_month_start(self) -> datetime:
        return datetime(self.dt.year, self.dt.month, 1, 0, 0, 0, tzinfo=EST)

    @property
    def _next_real_month_start(self) -> datetime:
        if self.dt.month == 12:
            return datetime(self.dt.year + 1, 1, 1, 0, 0, 0, tzinfo=EST)
        else:
            return datetime(self.dt.year, self.dt.month + 1, 1, 0, 0, 0, tzinfo=EST)

    @property
    def _seconds_since_dt_midnight(self) -> float:
        """Seconds since dt midnight."""
        today = datetime(self.dt.year, self.dt.month, self.dt.day, 0, 0, 0, tzinfo=EST)
        return (self.dt - today).total_seconds()

    @property
    def nights_since_dt_midnight(self) -> int:
        return int(self._seconds_since_dt_midnight // SECONDS_PER_NIGHT)

    # Clock

    @property
    def nightyears(self) -> int:
        """One real month is one nightyear.

        Dec 2025 (month=12, year=2025) is the BASE_NIGHTYEAR.
        """

        months_since_epoch = (self.dt.year - 2025) * 12 + (self.dt.month - 12)
        return BASE_NIGHTYEAR + months_since_epoch

    @property
    def moons(self) -> int:
        return self.dt.day

    @property
    def hours(self) -> int:
        """The current hour in 24-hour format from 06:00 to 02:00."""

        hour_index = int(self.elapsed_pct * HOURS_PER_NIGHT * 60) // 60  # 0..19
        hour_24 = 6 + hour_index  # 6 -> 25
        if hour_24 >= 24:
            hour_24 -= 24
        return hour_24

    @property
    def hours_float(self) -> float:
        """
        Continuous in-game hour in [0, 24), mapped from 06:00 -> 02:00
        over HOURS_PER_NIGHT hours.
        """
        total_night_minutes = self.elapsed_pct * HOURS_PER_NIGHT * 60.0
        hour_offset = total_night_minutes / 60.0  # 0..20
        h = 6.0 + hour_offset  # 6..26
        if h >= 24.0:
            h -= 24.0  # wrap to 0..24
        return h

    @property
    def minutes(self) -> int:
        return int(self.elapsed_pct * HOURS_PER_NIGHT * 60) % 60

    @property
    def seconds(self) -> float:
        return self._seconds_since_dt_midnight % SECONDS_PER_NIGHT

    @property
    def dawn(self) -> float:
        """Seasonal sunrise time in 24h hours (e.g. 6.0 = 06:00)."""
        s = self.nightyear_elapsed_pct  # 0..1
        angle = 2 * math.pi * s

        # Day length extremes: 10.5h (7:00–17:30) to 16h (6:00–22:00)
        avg_daylen = 13.25
        amp_daylen = 2.75

        # Center (midday) extremes: 12.25 to 14.0
        avg_center = 13.125
        amp_center = 0.875

        daylen = avg_daylen - amp_daylen * math.cos(angle)
        center = avg_center - amp_center * math.cos(angle)

        sunrise = center - daylen / 2.0
        return max(0.0, min(24.0, sunrise))

    @property
    def dusk(self) -> float:
        """Seasonal sunset time in 24h hours (e.g. 22.0 = 22:00)."""
        s = self.nightyear_elapsed_pct
        angle = 2 * math.pi * s

        avg_daylen = 13.25
        amp_daylen = 2.75

        avg_center = 13.125
        amp_center = 0.875

        daylen = avg_daylen - amp_daylen * math.cos(angle)
        center = avg_center - amp_center * math.cos(angle)

        sunset = center + daylen / 2.0
        return max(0.0, min(24.0, sunset))

    @property
    def elapsed_pct(self) -> float:
        """Percentage elapsed through the current night."""
        return self.seconds / (SECONDS_PER_NIGHT - SECONDS_PER_NIGHTSTORM)

    @property
    def nightyear_elapsed_pct(self) -> float:
        start = self._real_month_start
        end = self._next_real_month_start
        dur = (end - start).total_seconds()
        if dur <= 0:
            return 0.0
        elapsed = (self.dt - start).total_seconds()
        return elapsed / dur

    @property
    def next_hour_eta(self) -> float:
        hours_elapsed = math.floor(self.seconds / SECONDS_PER_NIGHT_HOUR)
        next = (hours_elapsed + 1) * SECONDS_PER_NIGHT_HOUR
        eta = next - self.seconds
        # clamp against floating noise and cycle end
        eta = max(
            0.0, min(eta, (SECONDS_PER_NIGHT - SECONDS_PER_NIGHTSTORM) - self.seconds)
        )
        return eta

    @property
    def seconds_remaining(self) -> float:
        return SECONDS_PER_NIGHT - self.seconds

    # Nightstorm

    @property
    def in_nightstorm(self) -> bool:
        remaining = SECONDS_PER_NIGHT - self.seconds
        return remaining <= SECONDS_PER_NIGHTSTORM and SECONDS_PER_NIGHTSTORM > 0

    @property
    def nightstorm_eta(self) -> float:
        start_t = SECONDS_PER_NIGHT - SECONDS_PER_NIGHTSTORM
        return start_t - self.seconds

    @property
    def nightstorm_elapsed_pct(self) -> float:
        if not self.in_nightstorm:
            return 0.0
        remaining = SECONDS_PER_NIGHT - self.seconds
        return 1.0 - (remaining / SECONDS_PER_NIGHTSTORM)

    # Epoch

    @property
    def seconds_since_epoch(self) -> float:
        return max(0.0, (self.dt - EPOCH).total_seconds())

    @property
    def nights_since_epoch(self) -> int:
        return self.moons_since_epoch * NIGHTS_PER_DAY + self.nights_since_dt_midnight

    @property
    def moons_since_epoch(self) -> int:
        return int(self.seconds_since_epoch // SECONDS_PER_DAY)

    @property
    def nights_this_nightyear(self) -> int:
        """Number of nights this nightyear.

        (since the start of the current real month).
        """
        start = self._real_month_start
        seconds_since_epoch_at_start = (start - EPOCH).total_seconds()
        moons_since_start = int(seconds_since_epoch_at_start // SECONDS_PER_DAY)
        cycles_before_year_start = moons_since_start * NIGHTS_PER_DAY
        current = self.nights_since_epoch
        return max(0, current - cycles_before_year_start)

    @property
    def brightness_index(self) -> int:
        """0-7 brightness index.

        - Nightstorm: 0 (full dark).
        - Deep night: ~1.
        - At seasonal dawn/dusk: ~4.
        - At seasonal noon: 7.
        """

        # Nightstorm overrides everything: world swallowed.
        if self.in_nightstorm:
            return 0

        h = self.hours_float  # 0..24
        sunrise = self.dawn  # between ~6 and 7
        sunset = self.dusk  # between ~17.5 and 22

        # Simple case: sunrise < sunset (true for our ranges)
        if sunrise <= h <= sunset:
            # Daytime: sin curve from 0.5 at edges to 1.0 at mid.
            # t=0 at sunrise, t=1 at sunset
            t = (h - sunrise) / (sunset - sunrise)
            t = max(0.0, min(1.0, t))

            # 0.5 at edges (dawn/dusk), 1.0 at mid (noon)
            brightness_norm = 0.5 + 0.5 * math.sin(math.pi * t)
        else:
            d = (24.0 - sunset) + h if h < sunrise else h - sunset

            # How quickly night darkens: after ~6 hours from the edge,
            # we are effectively at full dark.
            d_max = 6.0
            falloff = max(0.0, 1.0 - d / d_max)

            # Map to 0 .. 0.5 range so nights are <= dawn/dusk brightness.
            # 0 at deep night, 0.5 near transitions
            brightness_norm = 0.5 * falloff

        # Map normalized [0,1] to bands 1–7
        band = 1 + round(6.0 * brightness_norm)
        return max(1, min(7, band))
