from enum import StrEnum
import itertools

from fastapi import WebSocket


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
Connection = WebSocket
OwnerId = int

counter = itertools.count(1)


def serial() -> int:
    return next(counter)


INDEX_HTML = open("ninjamagic/static/index.html", "r").read()
LOGIN_HTML = open("ninjamagic/static/login.html", "r").read()
