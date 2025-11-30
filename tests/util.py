from pydantic.dataclasses import Field, dataclass

from ninjamagic.component import (
    Glyph,
    Health,
    Noun,
    Skills,
    Stance,
    Stats,
    Transform,
)


# TODO Just use the sqlc generated fake models. UpdateCharacterParams or whatever.
@dataclass
class FakeUserSetup:
    subj: str = "12023"
    email: str = "test@example.com"
    glyph: Glyph = ("@", 0.5833, 0.7, 0.828)
    health: Health = Field(default_factory=Health)
    stance: Stance = Field(default_factory=Stance)
    stats: Stats = Field(default_factory=Stats)
    skills: Skills = Field(default_factory=Skills)
    transform: Transform = Field(default_factory=lambda: Transform(map_id=1, x=2, y=2))
    noun: Noun = Field(default_factory=Noun)
