import colorsys
import itertools
from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto


class Reach(IntEnum):
    adjacent = auto()  # symmetric, transitive, reflexive
    visible = auto()  # symmetric, intransitive, reflexive


class Packets(StrEnum):
    Message = "m"
    Legend = "l"


@dataclass(frozen=True)
class ColorHSV:
    h: float  # Hue in [0, 360)
    s: float  # Saturation in [0, 1]
    v: float  # Value (brightness) in [0, 1]

    @classmethod
    def from_rgb(cls, r: float, g: float, b: float) -> "ColorHSV":
        """Create from RGB values in [0, 1]."""
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return cls(h * 360.0, s, v)

    def to_rgb(self) -> tuple[float, float, float]:
        """Convert to RGB values in [0, 1]."""
        r, g, b = colorsys.hsv_to_rgb(self.h / 360.0, self.s, self.v)
        return r, g, b

    def __str__(self) -> str:
        return f"HSV({self.h:.1f}, {self.s:.2f}, {self.v:.2f})"


class Compass(StrEnum):
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
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


@dataclass(slots=True, kw_only=True, frozen=True)
class Size:
    width: int
    height: int


@dataclass(slots=True, kw_only=True, frozen=True)
class Glyph:
    char: str
    color: ColorHSV


def serial(counter=itertools.count(1)) -> int:
    return next(counter)


OWNER = "user"
TILE_STRIDE = Size(width=13, height=13)
VIEW_STRIDE = Size(width=TILE_STRIDE.width // 2, height=TILE_STRIDE.height // 2)


INDEX_HTML = open("ninjamagic/static/index.html", "r").read()
LOGIN_HTML = open("ninjamagic/static/login.html", "r").read()
Walltime = float
