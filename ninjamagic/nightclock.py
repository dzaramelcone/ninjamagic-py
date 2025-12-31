import heapq
import math
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from functools import total_ordering
from typing import overload

from ninjamagic import bus
from ninjamagic.util import serial

EST = timezone(timedelta(hours=-5), name="EST")


HOURS_PER_NIGHT: int = 20  # 06:00 -> 02:00
# 18m or 36m in seconds; must divide 86400 or fix implementation
SECONDS_PER_NIGHT: float = 18.0 * 60.0
SECONDS_PER_NIGHTSTORM: float = 25.0
SECONDS_PER_NIGHTSTORM_HOUR: float = SECONDS_PER_NIGHTSTORM / (24 - HOURS_PER_NIGHT)
SECONDS_PER_NIGHT_ACTIVE: float = SECONDS_PER_NIGHT - SECONDS_PER_NIGHTSTORM
SECONDS_PER_NIGHT_HOUR: float = SECONDS_PER_NIGHT_ACTIVE / HOURS_PER_NIGHT

BASE_NIGHTYEAR: int = 200
EPOCH = datetime(2025, 12, 1, 0, 0, 0, tzinfo=EST)

SECONDS_PER_DAY = 86400.0
NIGHTS_PER_DAY = int(SECONDS_PER_DAY // SECONDS_PER_NIGHT)


def now():
    return datetime.now(tz=EST)


@total_ordering
class NightTime:
    def __init__(self, hour: int = 0, minute: int = 0):
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError

        self.hour = hour
        self.minute = minute

    def __eq__(self, other: "NightTime") -> bool:
        return self.total_seconds() == other.total_seconds()

    def __lt__(self, other: "NightTime") -> bool:
        return self.total_seconds() < other.total_seconds()

    def total_seconds(self) -> float:
        """Return the total seconds into the cycle for this time."""
        if 6 <= self.hour < 24:
            hour = self.hour - 6
        elif 0 <= self.hour < 2:
            hour = self.hour + 18
        else:
            # Nightstorm.
            offset = (self.hour - 2) * SECONDS_PER_NIGHTSTORM_HOUR
            offset += self.minute * SECONDS_PER_NIGHTSTORM_HOUR / 60.0
            return SECONDS_PER_NIGHT_ACTIVE + offset

        out = hour * SECONDS_PER_NIGHT_HOUR
        out += self.minute * SECONDS_PER_NIGHT_HOUR / 60.0
        return out

    @classmethod
    def from_seconds(cls, seconds: float) -> "NightTime":
        seconds = seconds % SECONDS_PER_NIGHT
        if seconds < SECONDS_PER_NIGHT_ACTIVE:
            hours = seconds / SECONDS_PER_NIGHT_HOUR
            hour = (6.0 + hours) % 24.0
        else:
            hours = (seconds - SECONDS_PER_NIGHT_ACTIVE) / SECONDS_PER_NIGHTSTORM_HOUR
            hour = 2.0 + hours

        hour, minute = divmod(hour, 1)
        return cls(hour=int(hour), minute=int(minute * 60))


class NightDelta:
    def __init__(
        self,
        *,
        nights: float = 0,
        hours: float = 0,
        minutes: float = 0,
        seconds: float = 0,
    ):
        self.seconds = nights * SECONDS_PER_NIGHT
        self.seconds += hours * SECONDS_PER_NIGHT_HOUR
        self.seconds += minutes * SECONDS_PER_NIGHT_HOUR / 60.0
        self.seconds += seconds

    def total_seconds(self) -> float:
        return self.seconds


@total_ordering
class NightClock:
    """Stateless, injective mapping from real-world EST timestamp to game time."""

    def __init__(self, dt: datetime | None = None):
        dt = dt or datetime.now(EST)
        dt = dt.astimezone(EST) if dt.tzinfo else dt.replace(tzinfo=EST)
        self.dt = dt

    def __eq__(self, other: "NightClock") -> bool:
        return self.dt == other.dt

    def __lt__(self, other: "NightClock") -> bool:
        return self.dt < other.dt

    def __add__(self, delta: NightDelta) -> "NightClock":
        return NightClock(dt=self.dt + timedelta(seconds=delta.total_seconds()))

    @overload
    def __sub__(self, other: "NightClock") -> NightDelta: ...
    @overload
    def __sub__(self, other: NightDelta) -> "NightClock": ...

    def __sub__(self, other: object) -> object:
        match other:
            case NightDelta():
                return NightClock(dt=self.dt - timedelta(seconds=other.total_seconds()))
            case NightClock():
                delta = (self.dt - other.dt).total_seconds()
                return NightDelta(seconds=delta)
            case _:
                return NotImplemented

    def to_now(self) -> None:
        self.dt = datetime.now(EST)

    def next(self, time: NightTime) -> NightDelta:
        target_seconds = time.total_seconds()
        if target_seconds > self.seconds:
            delta = target_seconds - self.seconds
        else:
            delta = (SECONDS_PER_NIGHT - self.seconds) + target_seconds
        return NightDelta(seconds=delta)

    def replace(self, time: NightTime) -> "NightClock":
        delta = timedelta(seconds=time.total_seconds() - self.seconds)
        return NightClock(self.dt + delta)

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

    @property
    def nightyears(self) -> int:
        """One real month is one nightyear.

        Dec 2025 (month=12, year=2025) is the BASE_NIGHTYEAR.
        """

        months_since_epoch = (self.dt.year - 2025) * 12 + (self.dt.month - 12)
        return BASE_NIGHTYEAR + months_since_epoch

    @property
    def hour(self) -> int:
        """The current hour in 24-hour format."""
        s = self.seconds

        if s < SECONDS_PER_NIGHT_ACTIVE:
            hour_index = int(s / SECONDS_PER_NIGHT_HOUR)
            h = 6 + hour_index
            if h >= 24:
                h -= 24
            return h

        else:
            storm_elapsed = s - SECONDS_PER_NIGHT_ACTIVE
            storm_hour_index = int(storm_elapsed / SECONDS_PER_NIGHTSTORM_HOUR)
            return 2 + storm_hour_index

    @property
    def hours_float(self) -> float:
        s = self.seconds
        if s < SECONDS_PER_NIGHT_ACTIVE:
            return (s / SECONDS_PER_NIGHT_HOUR + 6.0) % 24.0
        else:
            storm_elapsed = s - SECONDS_PER_NIGHT_ACTIVE
            return 2.0 + (storm_elapsed / SECONDS_PER_NIGHTSTORM_HOUR)

    @property
    def minute(self) -> int:
        s = self.seconds
        if s < SECONDS_PER_NIGHT_ACTIVE:
            rem = s % SECONDS_PER_NIGHT_HOUR
            return int(rem / SECONDS_PER_NIGHT_HOUR * 60)
        else:
            storm_elapsed = s - SECONDS_PER_NIGHT_ACTIVE
            rem = storm_elapsed % SECONDS_PER_NIGHTSTORM_HOUR
            return int(rem / SECONDS_PER_NIGHTSTORM_HOUR * 60)

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
        return min(self.seconds / SECONDS_PER_NIGHT_ACTIVE, 1.0)

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
        next_mark = (hours_elapsed + 1) * SECONDS_PER_NIGHT_HOUR
        eta = next_mark - self.seconds
        eta = max(0.0, min(eta, SECONDS_PER_NIGHT_ACTIVE - self.seconds))
        return eta

    # Nightstorm

    @property
    def in_nightstorm(self) -> bool:
        return self.seconds >= SECONDS_PER_NIGHT_ACTIVE

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


Rule = Generator[NightDelta]
Cue = tuple[NightClock, int, bus.Signal, Rule | None]
pq = list[Cue]()
clock = NightClock()


def cue_at(sig: bus.Signal, at: NightClock, recur: Rule | None = None) -> None:
    heapq.heappush(pq, (at, serial(), sig, recur))


def cue(
    sig: bus.Signal, time: NightTime | None = None, recur: Rule | None = None
) -> None:
    eta = clock + clock.next(time or NightTime())
    cue_at(sig, eta, recur)


def recurring(
    *, n_more_times: int, interval: NightDelta | None = None, forever: bool = False
) -> Rule:
    interval = interval or NightDelta(nights=1)
    i = 0
    while forever or i < n_more_times:
        yield interval
        i += 1


def process():
    clock.to_now()
    while pq and pq[0][0] <= clock:
        due, tiebreak, sig, recur = heapq.heappop(pq)
        bus.pulse(sig)
        if not recur:
            continue
        if eta := next(recur, None):
            heapq.heappush(pq, (due + eta, serial(), sig, recur))
