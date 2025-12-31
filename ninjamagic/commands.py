import asyncio
import logging
from typing import Protocol

import esper

from ninjamagic import bus, reach, story, util
from ninjamagic.component import (
    ContainedBy,
    Container,
    Cookware,
    Defending,
    EntityId,
    Health,
    Ingredient,
    Lag,
    Noun,
    Prompt,
    ProvidesHeat,
    Skills,
    Slot,
    Stance,
    Stowed,
    Stunned,
    Wearable,
    get_contents,
    get_hands,
    get_stored,
    get_worn,
    stance_is,
    transform,
)
from ninjamagic.config import settings
from ninjamagic.util import Compass, get_looptime, get_melee_delay
from ninjamagic.world.state import get_recall

log = logging.getLogger(__name__)
Out = tuple[bool, str]
OK = (True, "")


def assert_not_stunned(entity: EntityId) -> Out:
    if esper.has_component(entity, Stunned):
        return False, "You're stunned!"
    return OK


def assert_healthy(entity: EntityId) -> Out:
    health = esper.try_component(entity, Health)
    if health and health.condition != "normal":
        return False, f"You're {health.condition}!"
    return OK


def assert_standing(source: EntityId) -> Out:
    if not stance_is(source, "standing"):
        return False, "You must stand first."
    return OK


class Command(Protocol):
    text: str
    requires_healthy: bool = True
    requires_not_busy: bool = True
    requires_standing: bool = False

    def trigger(self, root: bus.Inbound) -> Out: ...


class Look(Command):
    text: str = "look"

    def trigger(self, root: bus.Inbound) -> Out:
        raw = root.text.strip().replace(" at ", " ")
        parsed = raw.replace(" in ", " ")
        look_in = parsed != raw

        _, _, rest = parsed.partition(" ")
        if not rest:
            return False, f"Look {"in" if look_in else "at"} what?"

        if look_in:
            match = match_contents(root.source, rest)
            match = match or next(
                reach.find(
                    root.source,
                    rest,
                    reach.adjacent,
                    with_components=(Container,),
                ),
                None,
            )
            if not match:
                return False, "Look in what?"
            eid, c_noun, _ = match
            if not esper.try_component(eid, Container):
                return False, f"You consider the inner beauty of {c_noun.definite()}."
            joined = util.INFLECTOR.join(
                [s_noun.indefinite() for _, s_noun, _ in get_contents(eid)]
            )
            bus.pulse(
                bus.Outbound(
                    to=root.source,
                    text=(
                        f"In {c_noun.indefinite()}, you see {joined}."
                        if joined
                        else f"{c_noun.definite()} has nothing in it.".capitalize()
                    ),
                )
            )
            return OK

        match = next(
            reach.find(source=root.source, prefix=rest, in_range=reach.visible), None
        )
        if not match:
            return False, "Look at what?"
        eid, _, _ = match
        story.echo("{0} {0:looks} at {1}.", root.source, eid)
        return OK


class Move(Command):
    text: str
    dir: Compass
    requires_standing: bool = True

    def __init__(self, text: str):
        self.text = text
        self.dir = Compass(self.text)

    def trigger(self, root: bus.Inbound) -> Out:
        bus.pulse(bus.MoveCompass(source=root.source, dir=self.dir))
        return OK


class Attack(Command):
    text: str = "attack"
    requires_standing: bool = True
    requires_not_busy: bool = False

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Attack whom?"
        match = next(
            reach.find(
                root.source,
                rest,
                reach.adjacent,
                with_components=(Health, Stance, Skills),
            ),
            None,
        )
        if not match:
            return False, "Attack whom?"

        target, _, _ = match

        health = esper.try_component(target, Health)
        if health and health.condition != "normal":
            return False, f"They're {health.condition}!"

        story.echo("{0} {0:draws} back {0:their} fist...", root.source, target)
        bus.pulse(
            bus.Act(
                source=root.source,
                delay=get_melee_delay(),
                then=(bus.Melee(source=root.source, target=target, verb="punch"),),
            ),
            bus.HealthChanged(source=root.source, stress_change=1.0),
        )
        return OK


class Forage(Command):
    text: str = "forage"
    requires_standing: bool = True
    requires_not_busy: bool = True

    def trigger(self, root: bus.Inbound) -> Out:
        story.echo("{0} {0:begins} to forage...", root.source)
        bus.pulse(
            bus.Act(
                source=root.source,
                delay=get_melee_delay(),
                then=(bus.Forage(source=root.source),),
            ),
            bus.HealthChanged(source=root.source, stress_change=1.0),
        )
        return OK


class Block(Command):
    text: str = "block"
    requires_standing: bool = True
    requires_not_busy: bool = False

    def trigger(self, root: bus.Inbound) -> Out:
        lag_len = settings.block_len + settings.block_miss_len
        this_block = Defending(verb="block")
        esper.add_component(root.source, util.get_looptime() + lag_len, Lag)
        esper.add_component(root.source, this_block)
        bus.pulse(
            bus.Interrupt(source=root.source),
            bus.Outbound(to=root.source, text=" "),
        )

        def stop_blocking():
            if not esper.entity_exists(root.source):
                return
            block = esper.try_component(root.source, Defending)
            if not block or block is not this_block:
                return
            esper.remove_component(root.source, Defending)
            bus.pulse(bus.Outbound(to=root.source, text="You block the air!"))

        asyncio.get_running_loop().call_later(settings.block_len, stop_blocking)
        return OK


class Say(Command):
    text: str = "say"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "You open your mouth, as if to speak."
        story.echo("{0} {0:says}, '{speech}'", root.source, speech=rest)
        return OK


class Stand(Command):
    text: str = "stand"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "standing"):
            return False, "You're already standing."
        bus.pulse(bus.StanceChanged(source=root.source, stance="standing", echo=True))
        return OK


class Lie(Command):
    text: str = "lie"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "lying prone"):
            return False, "You're already prone."
        bus.pulse(
            bus.StanceChanged(source=root.source, stance="lying prone", echo=True)
        )
        return OK


class Rest(Lie):
    text: str = "rest"


class Kneel(Command):
    text: str = "kneel"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "kneeling"):
            return False, "You're already kneeling."
        bus.pulse(bus.StanceChanged(source=root.source, stance="kneeling", echo=True))
        return OK


class Sit(Command):
    text: str = "sit"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "sitting"):
            return False, "You're already sitting."
        bus.pulse(bus.StanceChanged(source=root.source, stance="sitting", echo=True))
        return OK


class Fart(Command):
    text: str = "fart"

    def trigger(self, root: bus.Inbound) -> Out:
        tform = transform(root.source)
        story.echo("{0} {0:farts}.", root.source)
        bus.pulse(bus.CreateGas(loc=(tform.map_id, tform.y, tform.x)))

        esper.add_component(
            root.source,
            Prompt(
                text="inhale deeply",
                end=get_looptime() + 4.0,
                on_success=lambda: story.echo(
                    "{0} {0:empties} {0:their} lungs, then deeply {0:inhales} {0:their} own fart-stink.",
                    root.source,
                ),
                on_mismatch=lambda: story.echo(
                    "{0} {0:coughs} and {0:gags} trying to suck in the smell of {0:their} own fart!",
                    root.source,
                ),
                on_expired_success=lambda: story.echo(
                    "{0} {0:draws} back a deep breath, but only a faint memory remains of {0:their} fart.",
                    root.source,
                ),
                on_expired_mismatch=lambda: story.echo(
                    "{0} {0:draws} back a deep breath, then {0:lapses} into a coughing fit!",
                    root.source,
                ),
            ),
        )
        bus.pulse_in(1, bus.OutboundPrompt(to=root.source, text="inhale deeply"))
        return OK


class Stress(Command):
    text: str = "stress"

    def trigger(self, root: bus.Inbound) -> Out:
        try:
            amount = int(root.text.strip().split()[-1])
        except ValueError:
            amount = 2

        bus.pulse(bus.HealthChanged(source=root.source, stress_change=amount))
        return OK


class Get(Command):
    text: str = "get"

    def trigger(self, root: bus.Inbound) -> Out:
        l_hand, r_hand = get_hands(root.source)
        if l_hand and r_hand:
            return False, "Your hands are full!"
        dest = Slot.LEFT_HAND if r_hand else Slot.RIGHT_HAND

        cmd = root.text.strip().replace(" in ", " ")
        cmd = cmd.replace(" from ", " ")
        cmd, _, rest = cmd.partition(" ")
        first, _, second = rest.partition(" ")
        if not first:
            return False, "Get what?"

        if second:
            container = match_contents(root.source, second) or next(
                reach.find(
                    source=root.source,
                    prefix=second,
                    in_range=reach.adjacent,
                    with_components=(Container,),
                ),
                None,
            )
            if not container:
                return False, "Get from where?"

            c_eid, _, _ = container
            if not (stored := match_contents(c_eid, first)):
                return False, "That isn't in there."
            s_eid, _, _ = stored
            story.echo(
                "{0} {0:gets} {1} from {2}.",
                root.source,
                s_eid,
                c_eid,
                range=reach.visible,
            )
            bus.pulse(bus.MoveEntity(source=s_eid, container=root.source, slot=dest))
            return OK

        match = next(
            (
                (c_eid, (s_eid, s_noun, s_slot))
                for c_eid, (s_eid, s_noun, s_slot) in get_stored(root.source)
                if s_noun.matches(first)
            ),
            None,
        )
        if match:
            c_eid, (s_eid, _, _) = match
            story.echo(
                "{0} {0:gets} {1} from {2}.",
                root.source,
                s_eid,
                c_eid,
                range=reach.visible,
            )
            bus.pulse(bus.MoveEntity(source=s_eid, container=root.source, slot=dest))
            return OK

        if match := next(
            reach.find(
                root.source,
                rest,
                reach.adjacent,
                with_components=(Noun, ContainedBy, Slot),
            ),
            None,
        ):
            c_eid, _, _ = match
            story.echo("{0} {0:gets} {1}.", root.source, c_eid, range=reach.visible)
            bus.pulse(
                bus.MoveEntity(
                    source=c_eid,
                    container=root.source,
                    slot=dest,
                )
            )
            return OK

        return False, "Get what?"


def match_hands(source: EntityId, token: str) -> tuple[int, Noun, Slot] | None:
    l_hand, r_hand = get_hands(source)
    if r_hand and r_hand[1].matches(token):
        return r_hand
    elif l_hand and l_hand[1].matches(token):
        return l_hand
    return None


def match_contents(source: EntityId, token: str) -> tuple[int, Noun, Slot] | None:
    return next((i for i in get_contents(source) if i[1].matches(token)), None)


class Drop(Command):
    text: str = "drop"

    def trigger(self, root: bus.Inbound) -> Out:
        l_hand, r_hand = get_hands(root.source)
        if not l_hand and not r_hand:
            return False, "Your hands are empty!"

        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Drop what?"

        match = None
        if rest == "right":
            match = r_hand
        if rest == "left":
            match = l_hand
        match = match or match_hands(root.source, rest)
        if not match:
            return False, "Drop what?"

        eid, _, _ = match
        loc = transform(root.source)
        story.echo("{0} {0:drops} {1}.", root.source, eid, range=reach.visible)
        bus.pulse(
            bus.MovePosition(
                source=eid, to_map_id=loc.map_id, to_y=loc.y, to_x=loc.x, quiet=True
            )
        )
        return OK


class Wear(Command):
    text: str = "wear"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Wear what?"
        match = match_hands(root.source, rest)
        if not match:
            return False, "Wear what?"
        eid, _, _ = match
        if not esper.try_component(eid, Wearable):
            return False, "You can't wear that."

        slot = esper.component_for_entity(eid, Wearable).slot
        story.echo("{0} {0:wears} {1}.", root.source, eid, range=reach.visible)
        bus.pulse(bus.MoveEntity(source=eid, container=root.source, slot=slot))
        return OK


class Remove(Command):
    text: str = "remove"

    def trigger(self, root: bus.Inbound) -> Out:
        l_hand, r_hand = get_hands(root.source)
        if l_hand and r_hand:
            return False, "Your hands are full!"
        dest = Slot.LEFT_HAND if r_hand else Slot.RIGHT_HAND

        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Remove what?"

        worn = get_worn(root.source)
        match = next((item for item in worn if item[1].matches(rest)), None)
        if not match:
            return False, "Remove what?"

        eid, _, _ = match
        story.echo("{0} {0:removes} {1}.", root.source, eid, range=reach.visible)
        bus.pulse(bus.MoveEntity(source=eid, container=root.source, slot=dest))
        return OK


class Put(Command):
    text: str = "put"

    def trigger(self, root: bus.Inbound) -> Out:
        cmd = root.text.strip().replace(" in ", " ")
        cmd, _, rest = cmd.partition(" ")
        first, _, second = rest.partition(" ")
        if not first or not (stored := match_hands(root.source, first)):
            return False, "Put what?"
        s_eid, _, _ = stored

        c_eid = None
        if not second:
            return False, "Put that where?"

        container = match_contents(root.source, second)
        container = container or next(
            reach.find(
                source=root.source,
                prefix=second,
                in_range=reach.adjacent,
            ),
            None,
        )

        if not container:
            return False, "Put that where?"

        c_eid, _, _ = container
        if esper.has_component(c_eid, ProvidesHeat):
            if esper.has_components(s_eid, Container, Cookware):
                story.echo(
                    "{0} {0:puts} {1} over the heat of {2}...",
                    root.source,
                    s_eid,
                    c_eid,
                )
                bus.pulse(
                    bus.Act(
                        source=root.source,
                        delay=get_melee_delay(),
                        then=(bus.Cook(chef=root.source, pot=s_eid, heatsource=c_eid),),
                    )
                )
                return OK

            if esper.has_component(s_eid, Ingredient):
                story.echo(
                    "{0} {0:puts} {1} over the heat of {2}...",
                    root.source,
                    s_eid,
                    c_eid,
                )
                bus.pulse(
                    bus.Act(
                        source=root.source,
                        delay=get_melee_delay(),
                        then=(
                            bus.Roast(
                                chef=root.source, ingredient=s_eid, heatsource=c_eid
                            ),
                        ),
                    )
                )
                return OK

        if not esper.try_component(c_eid, Container):
            return False, "You can't put that there."

        if s_eid == c_eid:
            return (
                False,
                "You consider flipping that inside out for a moment.",
            )

        story.echo(
            "{0} {0:puts} {1} in {2}.", root.source, s_eid, c_eid, range=reach.visible
        )
        bus.pulse(bus.MoveEntity(source=s_eid, container=c_eid, slot=Slot.ANY))
        return OK


class Stow(Command):
    text: str = "stow"

    def trigger(self, root: bus.Inbound) -> Out:
        cmd = root.text.strip().replace(" in ", " ")
        cmd, _, rest = cmd.partition(" ")
        first, _, second = rest.partition(" ")
        if not first:
            return False, "Stow what?"

        match = match_hands(root.source, first)
        if not match:
            # Check on the floor if they have a free hand.
            l_hand, r_hand = get_hands(root.source)
            match = next(
                reach.find(
                    root.source,
                    first,
                    reach.adjacent,
                    with_components=(Noun, ContainedBy, Slot),
                ),
                None,
            )
            if match and l_hand and r_hand:
                return False, "Your hands are full!"

        if not match:
            return False, "Stow what?"

        s_eid, _, _ = match
        if not second and esper.try_component(root.source, Stowed):
            c_eid = esper.component_for_entity(root.source, Stowed).container
            loc = esper.try_component(c_eid, ContainedBy)
            if not loc or loc != root.source:
                esper.remove_component(root.source, Stowed)
                return False, "Stow that where?"
        elif second and (container := match_contents(root.source, second)):
            c_eid, _, _ = container
        else:
            return False, "Stow that where?"

        if not esper.try_component(c_eid, Container):
            return False, "You can't stow that there."

        if s_eid == c_eid:
            return (False, "You consider flipping it inside out, but decide not to.")

        story.echo(
            "{0} {0:stows} {1} in {2}.", root.source, s_eid, c_eid, range=reach.visible
        )
        bus.pulse(bus.MoveEntity(source=s_eid, container=c_eid, slot=Slot.ANY))
        esper.add_component(root.source, Stowed(container=c_eid))
        return OK


class Swap(Command):
    text: str = "swap"

    def trigger(self, root: bus.Inbound) -> Out:
        l_hand, r_hand = get_hands(root.source)
        if l_hand and r_hand:
            r_eid, _, _ = r_hand
            l_eid, _, _ = l_hand
            story.echo(
                "{0} {0:moves} {2} to {0:their} right hand and {1} to {0:their} left.",
                root.source,
                r_eid,
                l_eid,
            )
            bus.pulse(
                bus.MoveEntity(
                    source=r_eid, container=root.source, slot=Slot.LEFT_HAND
                ),
                bus.MoveEntity(
                    source=l_eid, container=root.source, slot=Slot.RIGHT_HAND
                ),
            )
        elif r_hand:
            r_eid, _, _ = r_hand
            story.echo("{0} {0:moves} {1} to {0:their} left hand.", root.source, r_eid)
            bus.pulse(
                bus.MoveEntity(
                    source=r_eid, container=root.source, slot=Slot.LEFT_HAND
                ),
            )
        elif l_hand:
            l_eid, _, _ = l_hand
            story.echo("{0} {0:moves} {1} to {0:their} left hand.", root.source, l_eid)
            bus.pulse(
                bus.MoveEntity(
                    source=l_eid, container=root.source, slot=Slot.RIGHT_HAND
                ),
            )
        else:
            story.echo("{0} {0:flaps} {0:their} hands about.", root.source)

        return OK


class Inventory(Command):
    text: str = "inventory"

    def trigger(self, root: bus.Inbound) -> Out:
        l_hand, r_hand = hands = get_hands(root.source)
        inv = get_contents(root.source)
        h_msg = ""

        if l_hand and r_hand:
            _, r_noun, _ = r_hand
            _, l_noun, _ = l_hand
            h_msg = f"You have {r_noun} in your right hand and {l_noun} in your left.\n"
        elif r_hand:
            _, noun, _ = r_hand
            h_msg = f"You have {noun} in your right hand.\n"
        elif l_hand:
            _, noun, _ = l_hand
            h_msg = f"You have {noun} in your left hand.\n"
        else:
            h_msg = ""

        w_msg = util.INFLECTOR.join([i[1].indefinite() for i in inv if i not in hands])
        w_msg = f"You are wearing {w_msg}." if w_msg else "You're naked!"

        bus.pulse(
            bus.Outbound(
                to=root.source,
                text=f"{h_msg}{w_msg}",
            )
        )
        return OK


class Recall(Command):
    text: str = "recall"

    def trigger(self, root: bus.Inbound) -> Out:
        to_map_id, to_y, to_x = get_recall(root.source)
        bus.pulse(
            bus.MovePosition(
                source=root.source, to_map_id=to_map_id, to_y=to_y, to_x=to_x
            )
        )
        return OK


commands: list[Command] = [
    *[Move(dir.value) for dir in Compass],
    *[Move(shortcut) for shortcut in ["ne", "se", "sw", "nw"]],
    Look(),
    Say(),
    Attack(),
    Stand(),
    Sit(),
    Lie(),
    Rest(),
    Kneel(),
    Block(),
    Fart(),
    Stress(),
    Recall(),
    Inventory(),
    Get(),
    Put(),
    Stow(),
    Drop(),
    Wear(),
    Remove(),
    Swap(),
    Forage(),
]
