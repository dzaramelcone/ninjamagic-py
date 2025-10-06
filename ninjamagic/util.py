import asyncio
import itertools
from dataclasses import dataclass
from enum import StrEnum
from typing import Sized


def clamp(x: float, lo: float, hi: float) -> float:
    return max(min(x, hi), lo)


def clamp01(x: float) -> float:
    return clamp(x, 0.0, 1.0)


def float_to_idx(obj: Sized, weight: float):
    n = len(obj)
    return min(n - 1, int(weight * n))


def remap(
    value: float,
    in_min: float,
    in_max: float,
    out_min: float = 0.0,
    out_max: float = 1.0,
) -> float:
    if in_max == in_min:
        raise ValueError("in_min and in_max must not be equal")
    t = (value - in_min) / (in_max - in_min)
    return out_min + t * (out_max - out_min)


class Compass(StrEnum):
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"
    NORTHEAST = "northeast"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    NORTHWEST = "northwest"

    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        match value:
            case "ne":
                return cls.NORTHEAST
            case "se":
                return cls.SOUTHEAST
            case "sw":
                return cls.SOUTHWEST
            case "nw":
                return cls.NORTHWEST
            case _:
                for member in cls:
                    if member.value == value:
                        return member
                return None

    def to_vector(self) -> tuple[int, int]:
        "Create a (y, x) tuple."
        match self:
            case Compass.NORTH:
                return (-1, 0)
            case Compass.NORTHEAST:
                return (-1, 1)
            case Compass.EAST:
                return (0, 1)
            case Compass.SOUTHEAST:
                return (1, 1)
            case Compass.SOUTH:
                return (1, 0)
            case Compass.SOUTHWEST:
                return (1, -1)
            case Compass.WEST:
                return (0, -1)
            case Compass.NORTHWEST:
                return (-1, -1)


@dataclass(slots=True, kw_only=True, frozen=True)
class Size:
    width: int
    height: int


def serial(counter=itertools.count(1)) -> int:
    return next(counter)


OWNER_SESSION_KEY = "user"
TILE_STRIDE = Size(width=16, height=16)
VIEW_STRIDE = Size(width=6, height=6)

VITE_HTML = open("ninjamagic/static/vite/index.html", "r").read()
BUILD_HTML = open("ninjamagic/static/gen/index.html", "r").read()
LOGIN_HTML = open("ninjamagic/static/login.html", "r").read()
MELEE_DELAY: float = 2.0

Walltime = float


def get_walltime() -> Walltime:
    return asyncio.get_running_loop().time()


def get_melee_delay() -> float:
    return MELEE_DELAY
