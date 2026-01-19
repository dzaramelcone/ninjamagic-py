from ninjamagic.gen.messages_pb2 import Packet
import ninjamagic.bus as bus
import ninjamagic.outbox as outbox


def test_outbound_skill_includes_pending():
    packet = Packet()
    env = packet.envelope
    sig = bus.OutboundSkill(to=1, name="Martial Arts", rank=1, tnl=0.5, pending=0.25)
    ok = outbox.try_insert(env, sig, 1, conn=None)
    assert ok
    assert env[0].skill.pending == 0.25
