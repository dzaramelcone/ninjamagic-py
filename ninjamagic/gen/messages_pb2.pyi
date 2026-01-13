from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Msg(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class Pos(_message.Message):
    __slots__ = ("id", "map_id", "x", "y", "quiet")
    ID_FIELD_NUMBER: _ClassVar[int]
    MAP_ID_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    QUIET_FIELD_NUMBER: _ClassVar[int]
    id: int
    map_id: int
    x: int
    y: int
    quiet: bool
    def __init__(self, id: _Optional[int] = ..., map_id: _Optional[int] = ..., x: _Optional[int] = ..., y: _Optional[int] = ..., quiet: bool = ...) -> None: ...

class Chip(_message.Message):
    __slots__ = ("id", "map_id", "glyph", "h", "s", "v", "a")
    ID_FIELD_NUMBER: _ClassVar[int]
    MAP_ID_FIELD_NUMBER: _ClassVar[int]
    GLYPH_FIELD_NUMBER: _ClassVar[int]
    H_FIELD_NUMBER: _ClassVar[int]
    S_FIELD_NUMBER: _ClassVar[int]
    V_FIELD_NUMBER: _ClassVar[int]
    A_FIELD_NUMBER: _ClassVar[int]
    id: int
    map_id: int
    glyph: int
    h: float
    s: float
    v: float
    a: float
    def __init__(self, id: _Optional[int] = ..., map_id: _Optional[int] = ..., glyph: _Optional[int] = ..., h: _Optional[float] = ..., s: _Optional[float] = ..., v: _Optional[float] = ..., a: _Optional[float] = ...) -> None: ...

class Tile(_message.Message):
    __slots__ = ("map_id", "top", "left", "data")
    MAP_ID_FIELD_NUMBER: _ClassVar[int]
    TOP_FIELD_NUMBER: _ClassVar[int]
    LEFT_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    map_id: int
    top: int
    left: int
    data: bytes
    def __init__(self, map_id: _Optional[int] = ..., top: _Optional[int] = ..., left: _Optional[int] = ..., data: _Optional[bytes] = ...) -> None: ...

class Gas(_message.Message):
    __slots__ = ("id", "map_id", "x", "y", "v")
    ID_FIELD_NUMBER: _ClassVar[int]
    MAP_ID_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    V_FIELD_NUMBER: _ClassVar[int]
    id: int
    map_id: int
    x: int
    y: int
    v: float
    def __init__(self, id: _Optional[int] = ..., map_id: _Optional[int] = ..., x: _Optional[int] = ..., y: _Optional[int] = ..., v: _Optional[float] = ...) -> None: ...

class Glyph(_message.Message):
    __slots__ = ("id", "glyph", "h", "s", "v")
    ID_FIELD_NUMBER: _ClassVar[int]
    GLYPH_FIELD_NUMBER: _ClassVar[int]
    H_FIELD_NUMBER: _ClassVar[int]
    S_FIELD_NUMBER: _ClassVar[int]
    V_FIELD_NUMBER: _ClassVar[int]
    id: int
    glyph: str
    h: float
    s: float
    v: float
    def __init__(self, id: _Optional[int] = ..., glyph: _Optional[str] = ..., h: _Optional[float] = ..., s: _Optional[float] = ..., v: _Optional[float] = ...) -> None: ...

class Noun(_message.Message):
    __slots__ = ("id", "text")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    id: int
    text: str
    def __init__(self, id: _Optional[int] = ..., text: _Optional[str] = ...) -> None: ...

class Health(_message.Message):
    __slots__ = ("id", "pct", "stress_pct")
    ID_FIELD_NUMBER: _ClassVar[int]
    PCT_FIELD_NUMBER: _ClassVar[int]
    STRESS_PCT_FIELD_NUMBER: _ClassVar[int]
    id: int
    pct: float
    stress_pct: float
    def __init__(self, id: _Optional[int] = ..., pct: _Optional[float] = ..., stress_pct: _Optional[float] = ...) -> None: ...

class Stance(_message.Message):
    __slots__ = ("id", "text")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    id: int
    text: str
    def __init__(self, id: _Optional[int] = ..., text: _Optional[str] = ...) -> None: ...

class Condition(_message.Message):
    __slots__ = ("id", "text")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    id: int
    text: str
    def __init__(self, id: _Optional[int] = ..., text: _Optional[str] = ...) -> None: ...

class Skill(_message.Message):
    __slots__ = ("name", "rank", "tnl")
    NAME_FIELD_NUMBER: _ClassVar[int]
    RANK_FIELD_NUMBER: _ClassVar[int]
    TNL_FIELD_NUMBER: _ClassVar[int]
    name: str
    rank: int
    tnl: float
    def __init__(self, name: _Optional[str] = ..., rank: _Optional[int] = ..., tnl: _Optional[float] = ...) -> None: ...

class Datetime(_message.Message):
    __slots__ = ("seconds",)
    SECONDS_FIELD_NUMBER: _ClassVar[int]
    seconds: int
    def __init__(self, seconds: _Optional[int] = ...) -> None: ...

class Prompt(_message.Message):
    __slots__ = ("text", "end")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    text: str
    end: float
    def __init__(self, text: _Optional[str] = ..., end: _Optional[float] = ...) -> None: ...

class Kind(_message.Message):
    __slots__ = ("msg", "pos", "chip", "tile", "gas", "glyph", "noun", "health", "stance", "condition", "skill", "datetime", "prompt")
    MSG_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    CHIP_FIELD_NUMBER: _ClassVar[int]
    TILE_FIELD_NUMBER: _ClassVar[int]
    GAS_FIELD_NUMBER: _ClassVar[int]
    GLYPH_FIELD_NUMBER: _ClassVar[int]
    NOUN_FIELD_NUMBER: _ClassVar[int]
    HEALTH_FIELD_NUMBER: _ClassVar[int]
    STANCE_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    SKILL_FIELD_NUMBER: _ClassVar[int]
    DATETIME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    msg: Msg
    pos: Pos
    chip: Chip
    tile: Tile
    gas: Gas
    glyph: Glyph
    noun: Noun
    health: Health
    stance: Stance
    condition: Condition
    skill: Skill
    datetime: Datetime
    prompt: Prompt
    def __init__(self, msg: _Optional[_Union[Msg, _Mapping]] = ..., pos: _Optional[_Union[Pos, _Mapping]] = ..., chip: _Optional[_Union[Chip, _Mapping]] = ..., tile: _Optional[_Union[Tile, _Mapping]] = ..., gas: _Optional[_Union[Gas, _Mapping]] = ..., glyph: _Optional[_Union[Glyph, _Mapping]] = ..., noun: _Optional[_Union[Noun, _Mapping]] = ..., health: _Optional[_Union[Health, _Mapping]] = ..., stance: _Optional[_Union[Stance, _Mapping]] = ..., condition: _Optional[_Union[Condition, _Mapping]] = ..., skill: _Optional[_Union[Skill, _Mapping]] = ..., datetime: _Optional[_Union[Datetime, _Mapping]] = ..., prompt: _Optional[_Union[Prompt, _Mapping]] = ...) -> None: ...

class Packet(_message.Message):
    __slots__ = ("envelope",)
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    envelope: _containers.RepeatedCompositeFieldContainer[Kind]
    def __init__(self, envelope: _Optional[_Iterable[_Union[Kind, _Mapping]]] = ...) -> None: ...
