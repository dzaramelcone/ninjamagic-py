from enum import StrEnum


class Color(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        match value:
            case "crimson":
                return cls.RED
        return None


print(Color("crimson"))
