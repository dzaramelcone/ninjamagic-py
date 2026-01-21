import esper

import ninjamagic.bus as bus
import ninjamagic.experience as experience
import ninjamagic.outbox as outbox
from ninjamagic.component import Skill, Skills
from ninjamagic.gen.messages_pb2 import Packet


def test_outbound_skill_includes_pending():
    packet = Packet()
    env = packet.envelope
    sig = bus.OutboundSkill(to=1, name="Martial Arts", rank=1, tnl=0.5, pending=0.25)
    ok = outbox.try_insert(env, sig, 1, conn=None)
    assert ok
    assert env[0].skill.pending == 0.25


def test_outbound_skill_has_pending_field():
    try:
        eid = esper.create_entity()
        esper.add_component(
            eid,
            Skills(martial_arts=Skill(name="Martial Arts", rank=1, tnl=0.5, pending=0.25)),
        )
        experience.send_skills(eid)
        sig = next(bus.iter(bus.OutboundSkill))
        assert sig.pending == 0.25
    finally:
        esper.clear_database()
        bus.clear()
