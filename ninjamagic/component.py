from collections.abc import Callable, Iterator
from dataclasses import dataclass, dataclass as component, field, fields
from enum import StrEnum, auto
from typing import Literal, NewType, TypeVar

import esper
from fastapi import WebSocket

from ninjamagic import util
from ninjamagic.config import settings
from ninjamagic.nightclock import NightClock
from ninjamagic.util import (
    TILE_STRIDE_H,
    TILE_STRIDE_W,
    Looptime,
    Num,
    Pronoun,
    Pronouns,
    get_looptime,
)

Biomes = Literal["cave", "forest"]
Conditions = Literal["normal", "unconscious", "in shock", "dead"]
Stances = Literal["standing", "kneeling", "sitting", "lying prone"]
ProcVerb = Literal["slash", "slice", "stab", "thrust", "punch", "dodge", "block", "shield", "parry"]
T = TypeVar("T")
EntityId = int
MAX_HEALTH = 100.0


@component(slots=True, kw_only=True)
class AABB:
    """Axis-aligned bounding box."""

    top: int
    bot: int
    left: int
    right: int

    def clear(self):
        self.top = self.bot = self.left = self.right = 0

    def contains(self, *, x: int, y: int) -> bool:
        return self.top <= y <= self.bot and self.left <= x <= self.right

    def intersects(self, *, other: "AABB") -> bool:
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bot < other.top
            or self.top > other.bot
        )

    def append(self, *, x: int, y: int):
        self.top = min(self.top, y)
        self.bot = max(self.bot, y)
        self.left = min(self.left, x)
        self.right = max(self.right, x)


ActId = NewType("ActId", int)


@dataclass(frozen=True)
class Armor:
    skill_key: str
    physical_immunity: float  # 0..1 (cap on how much it could block vs physical)
    magical_immunity: float  # 0..1 (cap vs magical)


CharacterId = NewType("CharacterId", int)
Chip = tuple[int, int, int, float, float, float]
Chips = dict[tuple[int, int], bytearray]
ChipSet = list[Chip]
Connection = WebSocket


class ProvidesHeat:
    """The entity provides heat. Used by cooking and camping."""


class ProvidesLight:
    """The entity provides light. Used by camping."""


@component(slots=True, kw_only=True)
class ProvidesShelter:
    """The entity can be used for shelter. Used by camping."""

    prompt: str


class Cookware:
    """Ingredients contained in this entity can be cooked together into a meal.

    Note the entity must have a Container component as well.
    """


class Ingredient:
    """Whether this entity can be cooked when exposed to a heat source.

    Example play use:
        - `put <entity> in <heat>`
        - `put <entity> in <cookware>`, then `put <cookware> in <heat>`
    """


@component(slots=True, frozen=True, kw_only=True)
class Food:
    count: int


@component(slots=True, frozen=True, kw_only=True)
class Ate:
    """The entity has eaten tonight. Used by camping."""

    meal_level: int
    pips: int


class Container:
    """Whether this entity can contain other entities. For example, bags or pots."""


class DoubleDamage:
    """A tag on an entity that causes its next attack to deal double damage.

    Consumed on use.
    """


@component(slots=True, kw_only=True)
class Defending:
    """The entity is currently defending.

    - `verb`: what type of defense they're using.
    """

    verb: ProcVerb


@component(slots=True, kw_only=True)
class LastAnchorRest:
    """When the entity last rested at an anchor."""

    nightclock: NightClock = field(default_factory=NightClock)

    def nights_since(self) -> float:
        now = NightClock()
        then = self.nightclock
        return (now - then).nights()


@component(slots=True, kw_only=True)
class Anchor:
    """Light against the darkness."""

    rank: int = 1
    tnl: float = 0
    rankup_echo: str


@dataclass
class SpawnSlot:
    """A spawn point within a den."""

    map_id: EntityId
    y: int
    x: int
    mob_eid: EntityId = 0
    kill_time: Looptime = 0
    spawn_time: Looptime = 0

    def is_ready(self, respawn_delay: float) -> bool:
        """Check if this slot is ready for (re)spawning."""
        if not self.mob_eid:
            return True  # never spawned
        if not esper.entity_exists(self.mob_eid):
            # Entity cleaned up - check cooldown
            return get_looptime() - self.kill_time > respawn_delay
        health = esper.component_for_entity(self.mob_eid, Health)
        if health.condition != "dead":
            return False  # mob alive
        return get_looptime() - self.kill_time > respawn_delay

    def clear(self) -> None:
        self.mob_eid = 0
        self.kill_time = 0
        self.spawn_time = 0


@component(slots=True)
class Den:
    """Mob spawn point with respawn logic."""

    slots: list[SpawnSlot] = field(default_factory=list)
    respawn_delay: float = 60.0  # 1 minute
    wake_distance: int = int(settings.pathing_distance)  # Chebyshev distance

    def clear(self) -> None:
        for slot in self.slots:
            slot.clear()


@component(slots=True)
class FromDen:
    """This mob was spawned by a den."""

    slot: SpawnSlot


@component(slots=True, kw_only=True)
class Sheltered:
    """The entity is sheltered by a `prop` with `Shelter`. Used by camping."""

    prop: EntityId


@component(slots=True, kw_only=True)
class FightTimer:
    """The entity has been in a fight recently.
    - `last_atk_proc`  used by the procs per minute system to award tokens on attack.
    - `last_def_proc`  used by the procs per minute system to award tokens on defense.
    - `last_refresh`   used to prevent logging out to escape combat.
    - `attacker`       who is currently attacking this entity.
    """

    last_atk_proc: Looptime
    last_def_proc: Looptime
    last_refresh: Looptime
    target: EntityId = 0

    def is_active(self) -> bool:
        return get_looptime() - self.last_refresh < settings.fight_timer_len

    def get_default_target(self) -> EntityId:
        if not self.is_active():
            return 0
        if not esper.entity_exists(self.target):
            return 0
        return self.target


Gas = NewType("Gas", dict[tuple[int, int], float])
Glyph = NewType("Glyph", tuple[str, float, float, float])


@component(slots=True)
class Health:
    """The well-being of an entity.

    - `cur` is the current health out of 100%.
    - `stress` is on a scale from 0-200, with >100 having "lost composure".
    - `aggravated_stress` is the minimum stress can be reduced to by resting.
    - `condition` represents their being unconscious, in shock, or dead.
    """

    cur: float = 100.0
    stress: float = 0.0
    aggravated_stress: float = 0.0
    condition: Conditions = "normal"


Lag = NewType("Lag", float)
Level = NewType("Level", int)
InventoryId = NewType("InventoryId", int)


@dataclass(frozen=True, slots=True)
class ItemKey:
    """The item type key, referencing ITEM_TYPES in inventory.py."""

    key: str


class DoNotSave:
    """Item should not be persisted to database."""
ContainedBy = NewType("ContainedBy", EntityId)


@component(slots=True, frozen=True)
class ForageEnvironment:
    default: tuple[Biomes, int]
    coords: dict[tuple[int, int], tuple[Biomes, int]] = field(default_factory=dict)

    def get_environment(self, y: int, x: int) -> tuple[Biomes, int]:
        y, x = y // TILE_STRIDE_H * TILE_STRIDE_H, x // TILE_STRIDE_W * TILE_STRIDE_W
        return self.coords.get((y, x), self.default)


@component(slots=True, frozen=True)
class Hostility:
    """The hostility rank at each tile. Used by eating and camping."""

    default: int
    coords: dict[tuple[int, int], int] = field(default_factory=dict)

    def get_rank(self, y: int, x: int) -> int:
        y, x = y // TILE_STRIDE_H * TILE_STRIDE_H, x // TILE_STRIDE_W * TILE_STRIDE_W
        return self.coords.get((y, x), self.default)


class Rotting:
    """The entity has started to rot. Used by food, unless you're giving Malenia."""


@component(slots=True, frozen=True)
class Noun:
    """How an entity is referred to.

    Used for generating stories in different perspectives and for searching and matching.
    """

    adjective: str = ""
    value: str = "thing"
    pronoun: Pronoun = Pronouns.IT
    num: Num = util.SINGULAR
    hypernyms: list[str] | None = None  # list of nouns?
    match_tokens: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.match_tokens.append(self.value)
        for i, m in enumerate(self.match_tokens):
            self.match_tokens[i] = m.strip().lower()

    def short(self) -> str:
        if self.adjective:
            return f"{self.adjective} {self.value}"
        return self.value

    def matches(self, prefix: str) -> bool:
        prefix = prefix.strip().lower()
        return any(s.startswith(prefix) for s in self.match_tokens)

    def definite(self) -> str:
        if self.value == "you":
            return "you"
        if self.value[0].isupper():
            return self.value
        return f"the {self.short()}"

    def indefinite(self) -> str:
        if self.value == "you":
            return "you"
        if self.value[0].isupper():
            return self.value
        if self.num == util.PLURAL:
            return f"some {self.short()}"
        return util.INFLECTOR.a(self.short())

    def __getattr__(self, key: str):
        return getattr(self.value, key)

    def __str__(self):
        return self.value

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return self.indefinite()
        if format_spec == "short":
            return self.short()
        if format_spec == "value":
            return self.value
        if format_spec == "s":
            return util.possessive(self.definite())
        if format_spec == "noun":
            return self.value
        if format_spec == "def":
            return self.definite()
        if format_spec == "hyp":
            if self.hypernyms:
                return util.RNG.choice(self.hypernyms)
            return self.value
        if format_spec == "hyps":
            if self.hypernyms:
                return util.possessive(util.RNG.choice(self.hypernyms))
            return util.possessive(self.value)
        if format_spec == "hyp_def":
            if self.hypernyms:
                return f"the {util.RNG.choice(self.hypernyms)}"
            return self.definite()
        if format_spec == "hyp_defs":
            if self.hypernyms:
                return util.possessive(f"the {util.RNG.choice(self.hypernyms)}")
            return util.possessive(self.definite())

        if pronoun := getattr(self.pronoun, format_spec, ""):
            return pronoun

        return util.conjugate(format_spec, self.num)


YOU = Noun(value="you", pronoun=Pronouns.YOU, num=util.PLURAL)
OwnerId = NewType("OwnerId", int)
Size = tuple[int, int]


@component(slots=True, kw_only=True)
class Prompt:
    """Whether an entity was prompted to type a phrase.

    These are single-shot commands with different outcomes dependent
    on whether `text` was typed correctly and whether it was before `end`.

    - `text` The text that needs to be typed.

    The following are all optional:

    - `end` The time the prompt will expire.
    - `on_ok` Called when response is `text` before `end`.
    - `on_err` Called when response is not `text` before `end`.
    - `on_expired_ok` Called when response is `text`, but after `end`.
    - `on_expired_err` Called when response is not `text` after `end`.

    If the callable for a branch is `None`, their input will be handled like a normal command.

    Note when all branches are set, the prompt must be responded to.
    """

    text: str
    end: Looptime = 0
    on_ok: Callable[[EntityId], None] | None = None
    on_err: Callable[[EntityId], None] | None = None
    on_expired_ok: Callable[[EntityId], None] | None = None
    on_expired_err: Callable[[EntityId], None] | None = None


@component(slots=True, kw_only=True)
class Skill:
    name: str
    rank: int = 0
    tnl: float = 0
    pending: float = 0.0
    rest_bonus: float = 1.0


@component(slots=True, kw_only=True)
class Skills:
    martial_arts: Skill = field(default_factory=lambda: Skill(name="Martial Arts"))
    evasion: Skill = field(default_factory=lambda: Skill(name="Evasion"))
    survival: Skill = field(default_factory=lambda: Skill(name="Survival"))

    def __iter__(self) -> Iterator[Skill]:
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, Skill):
                yield v

    def __getitem__(self, key: str) -> Skill:
        # First try field name lookup (e.g., "martial_arts")
        if hasattr(self, key):
            attr = getattr(self, key)
            if isinstance(attr, Skill):
                return attr
        # Fall back to display name matching (e.g., "Martial Arts")
        for s in self:
            if s.name == key:
                return s
        raise KeyError


@component(slots=True, kw_only=True)
class AwardCap:
    learners: dict[int, dict[str, tuple[float, float]]] = field(default_factory=dict)


@component(slots=True, kw_only=True)
class Stowed:
    container: EntityId


class Slot(StrEnum):
    ANY = ""
    RIGHT_HAND = "right hand"
    LEFT_HAND = "left hand"
    BACK = auto()
    SHOULDER = auto()
    ARMOR = auto()
    HEAD = auto()
    FEET = auto()


@component(slots=True)
class Stance:
    cur: Stances = "standing"
    prop: EntityId = 0

    def camping(self) -> bool:
        if self.cur not in ("sitting", "lying prone"):
            return False

        if not self.prop or not esper.entity_exists(self.prop):
            return False

        return esper.has_component(self.prop, ProvidesHeat) or esper.has_component(
            self.prop, ProvidesLight
        )


@component(slots=True, kw_only=True)
class Stats:
    grace: int = 0
    grit: int = 0
    wit: int = 0


@component(slots=True)
class Stunned:
    end: Looptime


@component(slots=True, kw_only=True)
class Transform:
    map_id: EntityId
    x: int
    y: int


@component(slots=True, kw_only=True)
class Wearable:
    slot: Slot


@component(slots=True, kw_only=True)
class Weapon:
    damage: float = 10.0
    token_key: str = "slash"
    story_key: str = "blade"
    skill_key: str = "martial_arts"


@component(slots=True, kw_only=True)
class Drives:
    """Layer weights. seek_ = toward goal, flee_ = relaxed escape routes."""

    seek_player: float = 0.0
    flee_player: float = 0.0
    seek_den: float = 0.0
    flee_anchor: float = 0.0


@component(slots=True, kw_only=True)
class Behavior:
    template: str = "goblin"
    state: str = "home"
    decision_interval: float = 0.33


def get_component[T](entity: EntityId, component: type[T]) -> T:
    return esper.component_for_entity(entity, component)


def transform(entity: EntityId) -> Transform:
    return get_component(entity, Transform)


def skills(entity: EntityId) -> Skills:
    return get_component(entity, Skills)


def health(entity: EntityId) -> Health:
    return get_component(entity, Health)


def pain_mult(entity: EntityId) -> float:
    return max(health(entity).cur / MAX_HEALTH, 0.005)


def client(entity: EntityId) -> Connection | None:
    return esper.try_component(entity, Connection)


def noun(entity: EntityId) -> Noun:
    return get_component(entity, Noun)


def stance(entity: EntityId) -> Stance:
    return get_component(entity, Stance)


def stance_is(entity: EntityId, check: Stances) -> bool:
    return stance(entity).cur == check


def get_contents(source: EntityId) -> list[tuple[EntityId, Noun, Slot]]:
    return [
        (eid, noun, slot)
        for eid, (noun, loc, slot) in esper.get_components(Noun, ContainedBy, Slot)
        if loc == source
    ]


def get_stored(source: EntityId) -> list[tuple[EntityId, tuple[EntityId, Noun, Slot]]]:
    return [
        (eid, item)
        for eid, (loc, _, _) in esper.get_components(ContainedBy, Slot, Container)
        if loc == source
        for item in get_contents(eid)
    ]


def get_hands(
    source: EntityId,
) -> tuple[tuple[EntityId, Noun, Slot] | None, tuple[EntityId, Noun, Slot] | None]:
    out = (None, None)
    for eid, (noun, loc, slot) in esper.get_components(Noun, ContainedBy, Slot):
        if loc != source:
            continue
        if slot == Slot.LEFT_HAND:
            out = ((eid, noun, slot), out[1])
        if slot == Slot.RIGHT_HAND:
            out = (out[0], (eid, noun, slot))
    return out


def get_worn(
    source: EntityId,
) -> list[tuple[EntityId, Noun, Slot]]:
    return [
        (eid, noun, slot)
        for eid, (noun, loc, slot) in esper.get_components(Noun, ContainedBy, Slot)
        if loc == source and slot not in (Slot.LEFT_HAND, Slot.RIGHT_HAND)
    ]


def get_wielded_weapon(source: EntityId) -> tuple[EntityId, Weapon] | None:
    """Get the entity ID of the weapon in source's hands, or 0 if unarmed."""
    for eid, (loc, slot) in esper.get_components(ContainedBy, Slot):
        if loc != source:
            continue
        if slot not in Slot.RIGHT_HAND:
            continue
        if weapon := esper.try_component(eid, Weapon):
            return eid, weapon
    return None


def get_worn_armor(source: EntityId) -> tuple[EntityId, Armor] | None:
    """Get the Armor component from source's worn armor slot, or None if unarmored."""

    for eid, (loc, slot) in esper.get_components(ContainedBy, Slot):
        if loc != source:
            continue
        if slot != Slot.ARMOR:
            continue
        if armor := esper.try_component(eid, Armor):
            return eid, armor
    return None
