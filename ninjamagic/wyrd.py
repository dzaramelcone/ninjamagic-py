"""Wyrd system: sacrifice at anchor to carry fire through darkness.

Decision tree:
1. Kneel at anchor (not already wyrd)
2. First prompt: "reach into the fire" → XP sacrifice
3. On fail: second prompt based on highest stat → stat sickness
4. On second fail: cancel
"""

import logging

import esper

from ninjamagic import bus, story
from ninjamagic.anchor import find_anchor_at, grow_anchor
from ninjamagic.component import (
    Anchor,
    Anima,
    ContainedBy,
    DamageTakenMultiplier,
    EntityId,
    Glyph,
    LastRestGains,
    Noun,
    ProcBonus,
    Prompt,
    Pronouns,
    Slot,
    Stats,
    StatSickness,
    Transform,
    Wyrd,
    get_hands,
)

log = logging.getLogger(__name__)

# Wyrd state modifiers
WYRD_DAMAGE_MULTIPLIER = 2.0
WYRD_PROC_BONUS = 0.1

# Stat sickness duration
STAT_SICKNESS_NIGHTS = 3


def get_highest_stat(player_eid: EntityId) -> str:
    """Get the player's highest stat name."""
    stats = esper.component_for_entity(player_eid, Stats)
    return max(["grace", "grit", "wit"], key=lambda s: getattr(stats, s))


def get_stat_prompt(stat: str) -> str:
    """Get the prompt text for a stat-based sacrifice."""
    prompts = {
        "grace": "catch the falling ash",
        "grit": "hold the coal",
        "wit": "name the flame",
    }
    return prompts[stat]


def create_anima(
    player_eid: EntityId,
    anchor_eid: EntityId,
    *,
    stat: str = "",
    skill: str = "",
    rank: int = 0,
) -> EntityId:
    """Create an anima entity in the player's hands."""
    anima_eid = esper.create_entity()

    esper.add_component(
        anima_eid,
        Anima(
            source_anchor=anchor_eid,
            source_player=player_eid,
            stat=stat,
            skill=skill,
            rank=rank,
        ),
    )
    esper.add_component(
        anima_eid,
        Noun(value="anima", pronoun=Pronouns.IT),
    )
    esper.add_component(
        anima_eid,
        ("*", 0.08, 0.9, 0.7),  # golden glow
        Glyph,
    )

    # Put in player's hands - find an empty hand
    l_hand, r_hand = get_hands(player_eid)
    if not l_hand:
        dest = Slot.LEFT_HAND
    elif not r_hand:
        dest = Slot.RIGHT_HAND
    else:
        # Hands full - drop left hand item first
        l_eid, _, _ = l_hand
        loc = esper.component_for_entity(player_eid, Transform)
        bus.pulse(
            bus.MovePosition(
                source=l_eid, to_map_id=loc.map_id, to_y=loc.y, to_x=loc.x, quiet=True
            ),
            bus.ItemDropped(source=player_eid, item=l_eid),
        )
        dest = Slot.LEFT_HAND

    # Add anima to player's hand directly (not via signal, for immediate availability)
    esper.add_component(anima_eid, player_eid, ContainedBy)
    esper.add_component(anima_eid, dest)

    return anima_eid


def enter_wyrd_state(
    player_eid: EntityId,
    anchor_eid: EntityId,
    *,
    stat: str = "",
    skill: str = "",
    rank: int = 0,
) -> None:
    """Put player into wyrd state with anima."""
    # Create anima
    anima_eid = create_anima(player_eid, anchor_eid, stat=stat, skill=skill, rank=rank)

    # Track which components we add for cleanup
    added = []

    # Add damage multiplier
    esper.add_component(player_eid, DamageTakenMultiplier(value=WYRD_DAMAGE_MULTIPLIER))
    added.append(DamageTakenMultiplier)

    # Add proc bonus
    esper.add_component(player_eid, ProcBonus(value=WYRD_PROC_BONUS))
    added.append(ProcBonus)

    # Add stat sickness if stat sacrifice
    if stat:
        esper.add_component(
            player_eid,
            StatSickness(stat=stat, nights_remaining=STAT_SICKNESS_NIGHTS),
        )
        added.append(StatSickness)

    # Mark as wyrd
    esper.add_component(player_eid, Wyrd(anima=anima_eid, added_components=added))

    # Grow source anchor
    player_rank = rank if rank else 1
    grow_anchor(anchor_eid, player_rank=player_rank)

    log.info(
        "wyrd_entered: player=%s anchor=%s stat=%s skill=%s",
        player_eid,
        anchor_eid,
        stat,
        skill,
    )


def exit_wyrd_state(player_eid: EntityId) -> None:
    """Remove wyrd state and cleanup."""
    wyrd = esper.try_component(player_eid, Wyrd)
    if not wyrd:
        return

    # Remove tracked components
    for comp_type in wyrd.added_components:
        if esper.has_component(player_eid, comp_type):
            esper.remove_component(player_eid, comp_type)

    # Remove wyrd marker
    esper.remove_component(player_eid, Wyrd)

    log.info("wyrd_exited: player=%s", player_eid)


def on_xp_sacrifice_ok(*, source: EntityId) -> None:
    """Player typed first prompt correctly - XP sacrifice."""
    transform = esper.component_for_entity(source, Transform)
    anchor_eid = find_anchor_at(transform.map_id, transform.y, transform.x)

    if not anchor_eid:
        story.echo("The fire has gone out.", source)
        return

    # Get last rest gains for XP value
    last_gains = esper.try_component(source, LastRestGains)
    if last_gains and last_gains.gains:
        # Use highest skill gain
        skill = max(last_gains.gains, key=last_gains.gains.get)
        rank = last_gains.gains[skill]
    else:
        skill = ""
        rank = 0

    enter_wyrd_state(source, anchor_eid, skill=skill, rank=rank)
    story.echo(
        "{0} {0:reaches} into the fire. Something tears free. {0} {0:holds} it now.",
        source,
    )


def on_xp_sacrifice_err(*, source: EntityId) -> None:
    """Player failed first prompt - offer stat sacrifice."""
    highest_stat = get_highest_stat(source)
    prompt_text = get_stat_prompt(highest_stat)

    # Store stat for the callback
    def on_stat_ok(*, source: EntityId, stat: str = highest_stat) -> None:
        on_stat_sacrifice_ok(source=source, stat=stat)

    esper.add_component(
        source,
        Prompt(
            text=prompt_text,
            on_ok=on_stat_ok,
            on_err=on_stat_sacrifice_err,
        ),
    )

    story.echo("You pull away. But it beckons within...", source)
    bus.pulse(bus.OutboundPrompt(to=source, text=prompt_text))


def on_stat_sacrifice_ok(*, source: EntityId, stat: str) -> None:
    """Player typed stat prompt correctly - stat sickness sacrifice."""
    transform = esper.component_for_entity(source, Transform)
    anchor_eid = find_anchor_at(transform.map_id, transform.y, transform.x)

    if not anchor_eid:
        story.echo("The fire has gone out.", source)
        return

    enter_wyrd_state(source, anchor_eid, stat=stat)
    story.echo(
        "{0} {0:grasps} something that burns. It leaves a mark.",
        source,
    )


def on_stat_sacrifice_err(*, source: EntityId) -> None:
    """Player failed both prompts - cancel."""
    story.echo("The moment passes.", source)


def start_wyrd_prompt(player_eid: EntityId, anchor_eid: EntityId) -> None:
    """Start the wyrd decision tree for a player at an anchor."""
    # Check not already wyrd
    if esper.has_component(player_eid, Wyrd):
        story.echo("You already carry the fire.", player_eid)
        return

    first_prompt = "reach into the fire"

    esper.add_component(
        player_eid,
        Prompt(
            text=first_prompt,
            on_ok=on_xp_sacrifice_ok,
            on_err=on_xp_sacrifice_err,
        ),
    )

    story.echo("The anchor's fire beckons...", player_eid)
    bus.pulse(bus.OutboundPrompt(to=player_eid, text=first_prompt))


def process() -> None:
    """Process wyrd-related signals."""
    # Handle player death - exit wyrd, destroy anima
    for sig in bus.iter(bus.Die):
        if esper.has_component(sig.source, Wyrd):
            wyrd = esper.component_for_entity(sig.source, Wyrd)
            anima_eid = wyrd.anima

            # Destroy anima
            if esper.entity_exists(anima_eid):
                esper.delete_entity(anima_eid)

            exit_wyrd_state(sig.source)
            story.echo("The anima fades into nothing.", sig.source)

    # Handle dropped anima - exit wyrd
    for sig in bus.iter(bus.ItemDropped):
        if not esper.has_component(sig.item, Anima):
            continue
        anima = esper.component_for_entity(sig.item, Anima)
        player_eid = anima.source_player
        if esper.has_component(player_eid, Wyrd):
            exit_wyrd_state(player_eid)
            story.echo("The anima slips from your grasp. The fire fades.", player_eid)

    # Handle kneeling at anchor - start wyrd prompt
    for sig in bus.iter(bus.StanceChanged):
        if sig.stance != "kneeling":
            continue
        if not sig.prop or not esper.has_component(sig.prop, Anchor):
            continue
        start_wyrd_prompt(sig.source, sig.prop)
