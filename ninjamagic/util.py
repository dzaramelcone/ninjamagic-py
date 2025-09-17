import colorsys
import itertools
from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto

VIEWSPAN = 7


class Reach(IntEnum):
    adjacent = auto()  # symmetric, transitive, reflexive
    visible = auto()  # symmetric, intransitive, reflexive


@dataclass(slots=True, frozen=True)
class Rect:
    """Axis-aligned rectangle."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    def clamp(self, width: int, height: int) -> "Rect":
        """Return a rect clamped to [0,width), [0,height)."""
        return Rect(
            left=max(0, min(width, self.left)),
            top=max(0, min(height, self.top)),
            right=max(0, min(width, self.right)),
            bottom=max(0, min(height, self.bottom)),
        )

    def intersect(self, other: "Rect") -> "Rect":
        """Return the intersection of this rect and another."""
        return Rect(
            left=max(self.left, other.left),
            top=max(self.top, other.top),
            right=min(self.right, other.right),
            bottom=min(self.bottom, other.bottom),
        )

    def to_slices(self) -> tuple[slice, slice]:
        """Return (yslice, xslice) for NumPy slicing."""
        return slice(self.top, self.bottom), slice(self.left, self.right)

    @staticmethod
    def from_size(left: int, top: int, width: int, height: int) -> "Rect":
        """Build a rect from top-left corner and size."""
        return Rect(left, top, left + width, top + height)

    @staticmethod
    def from_center(cx: int, cy: int, width: int, height: int) -> "Rect":
        """Build a rect centered on (cx, cy)."""
        half_w, half_h = width // 2, height // 2
        return Rect(cx - half_w, cy - half_h, cx - half_w + width, cy - half_h + height)


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


OWNER = "user"
counter = itertools.count(1)


def serial() -> int:
    return next(counter)


INDEX_HTML = open("ninjamagic/static/index.html", "r").read()
LOGIN_HTML = open("ninjamagic/static/login.html", "r").read()
Walltime = float
