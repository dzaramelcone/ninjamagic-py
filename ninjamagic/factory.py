import esper

from ninjamagic import bus
from ninjamagic.component import (
    CharId,
    EntityId,
    Glyph,
    Health,
    Noun,
    OwnerId,
    Skill,
    Skills,
    Stance,
    Stats,
    Transform,
    transform,
)
from ninjamagic.gen.models import Character
from ninjamagic.gen.query import UpdateCharacterParams
from ninjamagic.util import Pronouns
from ninjamagic.world.state import DEMO, NOWHERE

SPAWN = (DEMO, 8, 8)


def move_into_world(entity: EntityId):
    pos = transform(entity)
    bus.pulse(
        bus.PositionChanged(
            source=entity,
            from_map_id=0,
            from_x=0,
            from_y=0,
            to_map_id=pos.map_id,
            to_x=pos.x,
            to_y=pos.y,
        )
    )


def load(entity: EntityId, row: Character) -> EntityId:
    esper.add_component(entity, row.owner_id, OwnerId)
    esper.add_component(entity, row.id, CharId)
    esper.add_component(
        entity, Noun(value=row.name, pronoun=Pronouns.from_str(row.pronoun))
    )
    esper.add_component(entity, row.glyph, Glyph)
    esper.add_component(entity, Transform(map_id=row.map_id, x=row.x, y=row.y))
    esper.add_component(entity, Health(cur=row.health, condition=row.condition))
    esper.add_component(entity, Stance(cur=row.stance))
    esper.add_component(entity, Stats(grace=row.grace, grit=row.grit, wit=row.wit))
    esper.add_component(
        entity,
        Skills(
            martial_arts=Skill(
                name="Martial Arts",
                rank=row.rank_martial_arts,
                tnl=row.tnl_martial_arts,
            ),
            evasion=Skill(name="Evasion", rank=row.rank_evasion, tnl=row.tnl_evasion),
        ),
    )
    move_into_world(entity)
    return entity


def dump(entity: EntityId) -> UpdateCharacterParams:
    char_id = esper.component_for_entity(entity, CharId)
    glyph = esper.component_for_entity(entity, Glyph)
    noun = esper.component_for_entity(entity, Noun)
    pos = esper.component_for_entity(entity, Transform)
    health = esper.component_for_entity(entity, Health)
    stance = esper.component_for_entity(entity, Stance)
    stats = esper.component_for_entity(entity, Stats)
    skills = esper.component_for_entity(entity, Skills)
    return UpdateCharacterParams(
        id=char_id,
        glyph=glyph,
        pronoun=noun.pronoun.they,
        map_id=pos.map_id,
        x=pos.x,
        y=pos.y,
        health=health.cur,
        stress=health.stress,
        aggravated_stress=health.aggravated_stress,
        condition=health.condition,
        stance=stance.cur,
        grace=stats.grace,
        grit=stats.grit,
        wit=stats.wit,
        rank_evasion=skills.evasion.rank,
        tnl_evasion=skills.evasion.tnl,
        rank_martial_arts=skills.martial_arts.rank,
        tnl_martial_arts=skills.martial_arts.tnl,
    )


def create(entity: EntityId):
    # spawn point
    map, y, x = SPAWN
    esper.add_component(entity, Transform(map_id=map, x=x, y=y))
    esper.add_component(entity, "@", Glyph)
    esper.add_component(entity, Noun())
    esper.add_component(entity, Health())
    esper.add_component(entity, Stance())
    esper.add_component(entity, Skills())
    esper.add_component(entity, Stats())
    move_into_world(entity)


def destroy(entity: EntityId):
    pos = transform(entity)
    bus.pulse(
        bus.PositionChanged(
            source=entity,
            from_map_id=pos.map_id,
            from_x=pos.x,
            from_y=pos.y,
            to_map_id=NOWHERE,
            to_x=1,
            to_y=1,
        )
    )
    esper.delete_entity(entity=entity)
