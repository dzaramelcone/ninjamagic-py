from enum import StrEnum

from fastapi import WebSocket


class Cardinal(StrEnum):
    north = "north"
    northeast = "northeast"
    east = "east"
    southeast = "southeast"
    south = "south"
    southwest = "southwest"
    west = "west"
    northwest = "northwest"

    def _missing_(cls, value):
        value = value.lower()
        match value:
            case "ne":
                return cls.northeast
            case "se":
                return cls.southeast
            case "sw":
                return cls.southwest
            case "nw":
                return cls.northwest
            case _:
                for member in cls:
                    if member.value == value:
                        return member
                return None
ACCOUNT = "user"
Client = WebSocket
Email = str
Account = dict
