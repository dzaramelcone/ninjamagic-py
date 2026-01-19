import asyncio
import logging
from typing import Protocol

import esper

from ninjamagic import act, bus, reach, story, util
from ninjamagic.component import (
    Anchor,
    Connection,
    ContainedBy,
    Container,
    Cookware,
    Defending,
    EntityId,
    FightTimer,
    Food,
    Health,
    Ingredient,
    Lag,
    Noun,
    Prompt,
    ProvidesHeat,
    ProvidesLight,
    Skills,
    Slot,
    Stance,
    Stances,
    Stowed,
    Stunned,
    Weapon,
    Wearable,
    get_contents,
    get_hands,
    get_stored,
    get_worn,
    noun,
    stance_is,
    transform,
)
from ninjamagic.config import settings
from ninjamagic.nightclock import NightClock
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
            return False, f"Look {'in' if look_in else 'at'} what?"

        if look_in:
            match = match_contents(root.source, rest)
            match = match or reach.find_one(
                root.source,
                rest,
                reach.adjacent,
                with_components=(Container,),
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

        match = reach.find_one(source=root.source, prefix=rest, in_range=reach.visible)
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
        if act.being_attacked(root.source):
            now = get_looptime()
            if esper.has_component(root.source, Connection):
                esper.add_component(root.source, now + settings.stun_len, Lag)
            return False, "You're being attacked!"

        bus.pulse(bus.MoveCompass(source=root.source, dir=self.dir))
        return OK


class Attack(Command):
    text: str = "attack"
    requires_standing: bool = True
    requires_not_busy: bool = False

    def trigger(self, root: bus.Inbound) -> Out:
        target = 0
        _, _, rest = root.text.partition(" ")
        if match := reach.find_one(
            root.source,
            rest,
            reach.adjacent,
            with_components=(Health, Stance, Skills),
        ):
            target, _, _ = match
        elif ft := esper.try_component(root.source, FightTimer):
            target = ft.get_default_target()

        if not target:
            return False, "Attack whom?"

        target_health = esper.try_component(target, Health)
        if target_health and target_health.condition != "normal":
            return False, f"They're {target_health.condition}!"

        if act.attacked_by_other(root.source, target):
            return False, "They're being attacked!"

        _, right_hand = get_hands(root.source)
        story_key = "fist"
        i_eid = 0
        if right_hand:
            i_eid, _, _ = right_hand
            weapon = esper.try_component(i_eid, Weapon)
            if not weapon:
                return False, f"You can't attack with {noun(i_eid)}!"
            story_key = weapon.story_key

        story.echo(story.ATTACK[story_key], root.source, target, i_eid)
        bus.pulse(
            bus.Act(
                source=root.source,
                target=target,
                delay=get_melee_delay(),
                then=(bus.Melee(source=root.source, target=target, verb="punch"),),
            ),
            bus.HealthChanged(source=root.source, stress_change=1.0),
        )
        return OK


class Forage(Command):
    text: str = "forage"
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
    requires_not_busy: bool = False  # can cancel attacks

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
        if act.being_attacked(root.source):
            now = get_looptime()
            if esper.has_component(root.source, Connection):
                esper.add_component(root.source, now + settings.stun_len, Lag)
        story.echo("{0} {0:says}, '{speech}'", root.source, speech=rest)
        return OK


class Shout(Command):
    text: str = "shout"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Shout what?"
        story.echo("{0} {0:shouts}, '{rest}!'", root.source, rest=rest, range=reach.world)
        return OK


class Emote(Command):
    text: str = "emote"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Emote what?"
        story.echo("{0} {action}", root.source, action=rest)
        return OK


def handle_stance(new_stance: Stances, root: bus.Inbound, cmd: str, inf: str = "") -> Out:
    _, _, rest = root.text.strip().partition(" ")
    inf = inf or new_stance
    stance = esper.component_for_entity(root.source, Stance)
    if not rest or rest in ("here", "down"):
        if stance.cur == new_stance:
            return False, f"You're already {inf}."
        bus.pulse(bus.StanceChanged(source=root.source, stance=new_stance, echo=True))
        return OK

    match = reach.find_one(source=root.source, prefix=rest, in_range=reach.adjacent)
    if match:
        prop, _, _ = match
        if stance.cur == new_stance and prop == stance.prop:
            noun = esper.component_for_entity(prop, Noun)
            return False, f"You're already {inf} beside {noun:def}."

        bus.pulse(bus.StanceChanged(source=root.source, stance=new_stance, prop=prop, echo=True))
        return OK
    return False, f"{cmd} where?"


class Stand(Command):
    text: str = "stand"
    story: str = "{0} {0:starts} to stand up..."

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.strip().partition(" ")
        stance = esper.component_for_entity(root.source, Stance)

        if not rest or rest in ("here", "up"):
            if stance.cur == "standing":
                if stance.prop:
                    bus.pulse(bus.StanceChanged(source=root.source, stance="standing", echo=False))
                    story.echo("{0} {0:moves} away from {1}.", root.source, stance.prop)
                    return OK
                return False, "You're already standing."
            story.echo(Stand.story, root.source)
            bus.pulse(
                bus.Act(
                    source=root.source,
                    delay=get_melee_delay(),
                    then=(bus.StanceChanged(source=root.source, stance="standing", echo=True),),
                )
            )
            return OK

        match = reach.find_one(source=root.source, prefix=rest, in_range=reach.adjacent)
        if match:
            prop, _, _ = match
            if stance.cur == "standing":
                if prop == stance.prop:
                    noun = esper.component_for_entity(prop, Noun)
                    return False, f"You're already standing beside {noun:def}."
                bus.pulse(
                    bus.StanceChanged(source=root.source, stance="standing", prop=prop, echo=True)
                )
                return OK
            story.echo(Stand.story, root.source)
            then = bus.StanceChanged(source=root.source, stance="standing", prop=prop, echo=True)
            bus.pulse(bus.Act(source=root.source, delay=get_melee_delay(), then=(then,)))
            return OK
        return False, "Stand where?"


class Lie(Command):
    text: str = "lie"

    def trigger(self, root: bus.Inbound) -> Out:
        return handle_stance(new_stance="lying prone", root=root, cmd="Lie")


class Rest(Command):
    text: str = "rest"

    def trigger(self, root: bus.Inbound) -> Out:
        return handle_stance(new_stance="lying prone", root=root, cmd="Rest", inf="resting")


class Kneel(Command):
    text: str = "kneel"

    def trigger(self, root: bus.Inbound) -> Out:
        return handle_stance(new_stance="kneeling", cmd="Kneel", root=root)


class Sit(Command):
    text: str = "sit"

    def trigger(self, root: bus.Inbound) -> Out:
        return handle_stance(new_stance="sitting", root=root, cmd="Sit")


class Eat(Command):
    text: str = "eat"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.strip().partition(" ")
        if not rest:
            return False, "Eat what?"

        match = match_hands(root.source, rest)
        in_hands = bool(match)

        match = match or reach.find_one(source=root.source, prefix=rest, in_range=reach.adjacent)
        if not match:
            return False, "Eat what?"

        food, _, _ = match
        if not esper.has_component(food, Food):
            story.echo("{0} {0:stares} at {1} with a hungry look.", root.source, food)
            return OK
        if not in_hands:
            return False, "You're not holding that."

        # Auto-sit at anchor if one is in the same cell
        src_tf = transform(root.source)
        stance = esper.component_for_entity(root.source, Stance)
        auto_sat = False
        if found := reach.find_at(src_tf, Anchor):
            anchor, _ = found
            if stance.prop != anchor:
                bus.pulse(
                    bus.StanceChanged(source=root.source, stance="sitting", prop=anchor, echo=False)
                )
                auto_sat = True

        # Check eating conditions for feedback (use anchor if we auto-sat)
        prop = anchor if auto_sat else (stance.prop if esper.entity_exists(stance.prop) else 0)
        is_warm = prop and esper.has_component(prop, ProvidesHeat)
        is_lit = prop and esper.has_component(prop, ProvidesLight)
        is_lit = is_lit or NightClock().brightness_index >= 6
        is_safe = prop and esper.has_component(prop, Anchor)

        if auto_sat:
            story.echo("{0} {0:settles} by {1:def} to eat...", root.source, anchor)
        elif is_warm and is_lit and is_safe:
            story.echo("{0} {0:begins} to eat, content...", root.source)
        elif not is_lit:
            story.echo("{0} {0:eats} in the dark...", root.source)
        elif not is_warm:
            story.echo("{0} {0:shivers}, eating in the cold...", root.source)
        elif not is_safe:
            story.echo("{0} {0:eats} warily, eyes on the shadows...", root.source)
        else:
            story.echo("{0} {0:begins} to eat...", root.source)

        bus.pulse(
            bus.Act(
                source=root.source,
                delay=get_melee_delay(),
                then=(bus.Eat(source=root.source, food=food),),
            )
        )
        return OK


class Fart(Command):
    text: str = "fart"

    def trigger(self, root: bus.Inbound) -> Out:
        def _ok(source: EntityId) -> None:
            (
                story.echo(
                    "{0} {0:empties} {0:their} lungs, then deeply {0:inhales} {0:their} own fart-stink.",
                    source,
                ),
            )

        def _err(source: EntityId) -> None:
            (
                story.echo(
                    "{0} {0:coughs} and {0:gags} trying to suck in the smell of {0:their} own fart!",
                    source,
                ),
            )

        def _ok_exp(source: EntityId) -> None:
            (
                story.echo(
                    "{0} {0:draws} back a deep breath, but only a faint memory remains of {0:their} fart.",
                    source,
                ),
            )

        def _err_exp(source: EntityId) -> None:
            (
                story.echo(
                    "{0} {0:draws} back a deep breath, then {0:lapses} into a coughing fit!",
                    source,
                ),
            )

        tform = transform(root.source)
        story.echo("{0} {0:farts}.", root.source)
        bus.pulse(bus.CreateGas(loc=(tform.map_id, tform.y, tform.x)))

        esper.add_component(
            root.source,
            Prompt(
                text="inhale deeply",
                end=get_looptime() + 4.0,
                on_ok=_ok,
                on_err=_err,
                on_expired_ok=_ok_exp,
                on_expired_err=_err_exp,
            ),
        )
        bus.pulse(bus.OutboundPrompt(to=root.source, text="inhale deeply"))
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


class Time(Command):
    text: str = "time"

    def trigger(self, root: bus.Inbound) -> Out:
        bus.pulse(
            bus.Outbound(
                to=root.source,
                text=str(NightClock()),
            )
        )
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
            container = match_contents(root.source, second) or reach.find_one(
                source=root.source,
                prefix=second,
                in_range=reach.adjacent,
                with_components=(Container,),
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

        if match := reach.find_one(
            root.source,
            rest,
            reach.adjacent,
            with_components=(Noun, ContainedBy, Slot),
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
            bus.MovePosition(source=eid, to_map_id=loc.map_id, to_y=loc.y, to_x=loc.x, quiet=True)
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
        container = container or reach.find_one(
            source=root.source,
            prefix=second,
            in_range=reach.adjacent,
        )

        if not container:
            return False, "Put that where?"

        c_eid, _, _ = container
        if esper.has_component(c_eid, ProvidesHeat):
            if esper.has_components(s_eid, Container, Cookware):
                story.echo(
                    "{0} {0:puts} {1} in the heat of {2}...",
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
                    "{0} {0:puts} {1} in the heat of {2}...",
                    root.source,
                    s_eid,
                    c_eid,
                )
                bus.pulse(
                    bus.Act(
                        source=root.source,
                        delay=get_melee_delay(),
                        then=(bus.Roast(chef=root.source, ingredient=s_eid, heatsource=c_eid),),
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

        story.echo("{0} {0:puts} {1} in {2}.", root.source, s_eid, c_eid, range=reach.visible)
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
            match = reach.find_one(
                root.source,
                first,
                reach.adjacent,
                with_components=(Noun, ContainedBy, Slot),
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

        story.echo("{0} {0:stows} {1} in {2}.", root.source, s_eid, c_eid, range=reach.visible)
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
                bus.MoveEntity(source=r_eid, container=root.source, slot=Slot.LEFT_HAND),
                bus.MoveEntity(source=l_eid, container=root.source, slot=Slot.RIGHT_HAND),
            )
        elif r_hand:
            r_eid, _, _ = r_hand
            story.echo("{0} {0:moves} {1} to {0:their} left hand.", root.source, r_eid)
            bus.pulse(
                bus.MoveEntity(source=r_eid, container=root.source, slot=Slot.LEFT_HAND),
            )
        elif l_hand:
            l_eid, _, _ = l_hand
            story.echo("{0} {0:moves} {1} to {0:their} left hand.", root.source, l_eid)
            bus.pulse(
                bus.MoveEntity(source=l_eid, container=root.source, slot=Slot.RIGHT_HAND),
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
        _, to_map_id, to_y, to_x = get_recall(root.source)
        bus.pulse(bus.MovePosition(source=root.source, to_map_id=to_map_id, to_y=to_y, to_x=to_x))
        return OK


class Announce(Command):
    text: str = "announce"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Announce what?"
        story.echo(rest, range=reach.world)
        return OK


HELP_TEXTS: dict[str, tuple[str, str]] = {
    "look": (
        "look at <target>\nlook in <container>",
        "Look at something or in a container.",
    ),
    "say": ("say <message>\n'<message>", "Say something out loud."),
    "shout": ("shout <message>", "Shout to the whole world."),
    "emote": ("emote <action>", "Perform an action/emote."),
    "attack": ("attack <target>", "Attack a target."),
    "stand": ("stand [beside <target>]", "Stand up."),
    "sit": ("sit [beside <target>]", "Sit down."),
    "lie": ("lie [beside <target>]", "Lie down."),
    "rest": ("rest [beside <target>]", "Rest (lie down)."),
    "kneel": ("kneel [beside <target>]", "Kneel down."),
    "block": ("block", "Raise your guard."),
    "recall": ("recall", "Return to your bind point."),
    "inventory": ("inventory", "View your inventory."),
    "get": ("get <item>\nget <item> from <container>", "Pick up an item."),
    "put": ("put <item> in <container>", "Put an item somewhere."),
    "stow": ("stow <item> [in <container>]", "Stow an item in a container."),
    "drop": ("drop <item>", "Drop an item."),
    "wear": ("wear <item>", "Wear an item."),
    "remove": ("remove <item>", "Remove worn item."),
    "swap": ("swap", "Swap items between hands."),
    "forage": ("forage", "Forage for items."),
    "eat": ("eat <food>", "Eat food."),
    "time": ("time", "Check the current time."),
    "help": ("help [command]", "Get help for a command, or list all commands."),
}


class Help(Command):
    text: str = "help"
    requires_healthy: bool = False
    requires_not_busy: bool = False
    requires_standing: bool = False

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        rest = rest.strip().lower()

        if not rest:
            hidden = {
                *[d.value for d in Compass],
                "ne",
                "nw",
                "se",
                "sw",
                "stress",
                "announce",
            }
            cmd_names = sorted({cmd.text for cmd in commands} - hidden)
            width = max(len(name) for name in cmd_names) + 2
            rows = []
            for i in range(0, len(cmd_names), 5):
                row = [name.ljust(width) for name in cmd_names[i : i + 5]]
                rows.append("".join(row).rstrip())
            grid = "\n".join(rows)
            bus.pulse(
                bus.Outbound(
                    to=root.source,
                    text=f"Commands:\n{grid}\n\nType 'help <command>' for details.",
                )
            )
            return OK

        if rest == "help help":
            bus.pulse(bus.Outbound(to=root.source, text="You need somebody."))
            return OK

        if rest == "help":
            usage, desc = HELP_TEXTS["help"]
            usage_lines = "\n".join(f"  {line}" for line in usage.split("\n"))
            bus.pulse(bus.Outbound(to=root.source, text=f"Usage:\n{usage_lines}\n\n  {desc}"))
            return OK

        cmd_match = None
        for cmd in commands:
            if cmd.text.startswith(rest):
                cmd_match = cmd
                break

        if not cmd_match:
            bus.pulse(
                bus.Outbound(to=root.source, text=f"No command '{rest}'. Type 'help' for list.")
            )
            return OK

        if help_entry := HELP_TEXTS.get(cmd_match.text):
            usage, desc = help_entry
            usage_lines = "\n".join(f"  {line}" for line in usage.split("\n"))
            text = f"Usage:\n{usage_lines}\n\n  {desc}"
        else:
            text = f"No help available for '{cmd_match.text}'."

        bus.pulse(bus.Outbound(to=root.source, text=text))
        return OK


commands: list[Command] = [
    *[Move(dir.value) for dir in Compass],
    *[Move(shortcut) for shortcut in ["ne", "se", "sw", "nw"]],
    Look(),
    Say(),
    Shout(),
    Emote(),
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
    Announce(),
    Inventory(),
    Get(),
    Put(),
    Stow(),
    Drop(),
    Wear(),
    Remove(),
    Swap(),
    Forage(),
    Eat(),
    Time(),
    Help(),
]
