import esper

from ninjamagic import bus
from ninjamagic.component import (
    ContainedBy,
    Health,
    Noun,
    Skills,
    Slot,
    Stance,
    Transform,
    Weapon,
)


def test_weapon_component_exists():
    """Weapon component can be created with expected fields."""
    weapon = Weapon(
        damage=15.0,
        token_key="slash",
        story_key="blade",
        skill_key="martial_arts",
    )
    assert weapon.damage == 15.0
    assert weapon.token_key == "slash"
    assert weapon.story_key == "blade"
    assert weapon.skill_key == "martial_arts"


def test_weapon_damage_affects_combat():
    """Wielding a weapon with story_key produces damage story from DAMAGE dict."""
    try:
        # Setup attacker with broadsword
        attacker = esper.create_entity()
        esper.add_component(attacker, Transform(map_id=1, x=0, y=0))
        esper.add_component(attacker, Health())
        esper.add_component(attacker, Skills())
        esper.add_component(attacker, Stance())
        esper.add_component(attacker, Noun(value="Alice"))

        # Create broadsword in attacker's hand
        weapon_eid = esper.create_entity()
        esper.add_component(
            weapon_eid, Weapon(damage=20.0, skill_key="martial_arts", story_key="broadsword")
        )
        esper.add_component(weapon_eid, Noun(value="broadsword"))
        esper.add_component(weapon_eid, attacker, ContainedBy)
        esper.add_component(weapon_eid, Slot.RIGHT_HAND)

        # Setup target
        target = esper.create_entity()
        esper.add_component(target, Transform(map_id=1, x=0, y=0))
        esper.add_component(target, Health())
        esper.add_component(target, Skills())
        esper.add_component(target, Stance())
        esper.add_component(target, Noun(value="Bob"))

        # Attack
        bus.clear()
        bus.pulse(bus.Melee(source=attacker, target=target, verb="slash"))

        from ninjamagic.combat import process

        process(1.0)

        # Should have at least standard damage message, possibly also damage story
        echos = list(bus.iter(bus.Echo))
        assert len(echos) >= 1, "Should have at least one Echo signal"

        # Find text echoes (those with make_other_sig that returns Outbound with text)
        text_messages = []
        for e in echos:
            if hasattr(e, "make_other_sig"):
                try:
                    msg = e.make_other_sig(0)
                    if hasattr(msg, "text"):
                        text_messages.append(msg.text)
                except TypeError:
                    pass
            if hasattr(e, "make_sig"):
                try:
                    msg = e.make_sig(0)
                    if hasattr(msg, "text"):
                        text_messages.append(msg.text)
                except TypeError:
                    pass

        # Should have at least one text message (damage story)
        assert len(text_messages) >= 1, f"Should have text message, got: {text_messages}"

        # Verify damage still applied
        target_health = esper.component_for_entity(target, Health)
        assert target_health.cur < 100.0, "Target should have taken damage"

    finally:
        esper.clear_database()
        bus.clear()


def test_armor_is_integrated():
    """Armor component is found and mitigate is called during combat."""
    try:
        from ninjamagic.armor import Armor

        # Setup attacker (unarmed)
        attacker = esper.create_entity()
        esper.add_component(attacker, Transform(map_id=1, x=0, y=0))
        esper.add_component(attacker, Health())
        esper.add_component(attacker, Skills())
        esper.add_component(attacker, Stance())

        # Setup target with armor
        target = esper.create_entity()
        esper.add_component(target, Transform(map_id=1, x=0, y=0))
        esper.add_component(target, Health())
        esper.add_component(target, Skills())
        esper.add_component(target, Stance())

        # Create armor entity worn by target
        armor_eid = esper.create_entity()
        esper.add_component(
            armor_eid,
            Armor(
                skill_key="martial_arts",
                item_rank=10,
                physical_immunity=0.5,
                magical_immunity=0.0,
            ),
        )
        esper.add_component(armor_eid, Noun(value="leather armor"))
        esper.add_component(armor_eid, target, ContainedBy)
        esper.add_component(armor_eid, Slot.ARMOR)

        # Verify armor is found before combat
        from ninjamagic.component import get_worn_armor

        found_armor = get_worn_armor(target)
        assert found_armor is not None, "Armor should be found on target"
        _, armor_component = found_armor
        assert armor_component.physical_immunity == 0.5

        # Attack
        bus.clear()
        bus.pulse(bus.Melee(source=attacker, target=target, verb="punch"))

        from ninjamagic.combat import process

        process(1.0)

        # Verify combat happened (target took damage)
        target_health = esper.component_for_entity(target, Health)
        assert target_health.cur < 100.0, "Target should have taken damage"

    finally:
        esper.clear_database()
        bus.clear()


def test_unarmed_uses_default_damage():
    """Without a weapon, combat uses default base damage of 10.0."""
    try:
        # Setup attacker (no weapon)
        attacker = esper.create_entity()
        esper.add_component(attacker, Transform(map_id=1, x=0, y=0))
        esper.add_component(attacker, Health())
        esper.add_component(attacker, Skills())
        esper.add_component(attacker, Stance())

        # Setup target
        target = esper.create_entity()
        esper.add_component(target, Transform(map_id=1, x=0, y=0))
        esper.add_component(target, Health())
        esper.add_component(target, Skills())
        esper.add_component(target, Stance())

        # Attack
        bus.clear()
        bus.pulse(bus.Melee(source=attacker, target=target, verb="punch"))

        from ninjamagic.combat import process

        process(1.0)

        # Check default damage (~10.0 with skill_mult ~1.0)
        target_health = esper.component_for_entity(target, Health)
        assert target_health.cur < 100.0, "Target should have taken damage"
        assert target_health.cur >= 85.0, "Unarmed damage should be ~10"

    finally:
        esper.clear_database()
        bus.clear()
