import asyncio

import pytest

from ninjamagic.component import Health, Noun, Skill, Skills, Transform
from ninjamagic.util import VIEW_STRIDE, Pronouns, get_melee_delay
from ninjamagic.world.state import TEST
from tests.util import FakeUserSetup

H, W = VIEW_STRIDE
INSIDE = W
OUTSIDE = INSIDE + 1


@pytest.fixture
def alice_setup() -> FakeUserSetup:
    return FakeUserSetup(
        subj="alice",
        email="alice@x.test",
        noun=Noun(value="Alice", pronoun=Pronouns.SHE),
    )


@pytest.fixture
def bob_setup() -> FakeUserSetup:
    return FakeUserSetup(
        subj="bob",
        email="bob@x.test",
        noun=Noun(value="Bob", pronoun=Pronouns.HE),
    )


@pytest.mark.asyncio
async def test_solo_client(golden, client_factory, alice_setup) -> None:
    alice = await client_factory(alice_setup, discard_init=False)

    async with asyncio.timeout(1):
        golden("alice", await alice.recv())

        await alice.send("asdok")
        golden("alice", await alice.recv())

        await alice.send("'")
        golden("alice", await alice.recv())

        await alice.send("'hi!")
        golden("alice", await alice.recv())


@pytest.mark.asyncio
async def test_chat(golden, client_factory, alice_setup, bob_setup):
    alice = await client_factory(alice_setup)
    bob = await client_factory(bob_setup)
    await alice.recv()
    async with asyncio.timeout(1):
        await alice.send("say hi")
        golden("alice", await alice.recv())
        golden("bob", await bob.recv())

        await bob.send("'hello")
        golden("alice", await alice.recv())
        golden("bob", await bob.recv())


@pytest.mark.asyncio
async def test_moves(golden, client_factory):
    alice = await client_factory(
        FakeUserSetup(
            subj="alice",
            email="alice@x.test",
            transform=Transform(map_id=TEST, x=6, y=6),
            noun=Noun(value="Alice", pronoun=Pronouns.SHE),
        ),
    )

    bob = await client_factory(
        FakeUserSetup(
            subj="bob",
            email="bob@x.test",
            transform=Transform(map_id=TEST, x=6 + OUTSIDE, y=6 + OUTSIDE),
            noun=Noun(value="Bob", pronoun=Pronouns.HE),
        ),
    )

    # alice should not see bob while he is outside
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.25):
            await alice.recv()

    # bob walks diagonally northwest into range
    async with asyncio.timeout(0.25):
        await bob.send("nw")
        golden("bob", await bob.recv())

    # alice should now see bob enter
    async with asyncio.timeout(0.25):
        golden("alice", await alice.recv())

    # bob walks southeast back out
    async with asyncio.timeout(1):
        await bob.send("se")
        golden("bob", await bob.recv())
        await bob.send("se")
        golden("bob", await bob.recv())

    # alice should see bob leave
    async with asyncio.timeout(0.25):
        golden("alice", await alice.recv())
    # but not any more than that
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.25):
            await alice.recv()

    # and he shouldn't be visible to the se either
    async with asyncio.timeout(0.25):
        await alice.send("se")
        golden("alice", await alice.recv())


@pytest.mark.asyncio
async def test_combat_and_exp(golden, client_factory):
    alice = await client_factory(
        FakeUserSetup(
            subj="alice",
            email="alice@x.test",
            health=Health(cur=4.0),  # she's very hurt
            skills=Skills(
                martial_arts=Skill(name="Martial Arts", tnl=4.0),
                evasion=Skill(name="Evasion", tnl=4.0),
            ),
            noun=Noun(value="Alice", pronoun=Pronouns.SHE),
        ),
    )

    bob = await client_factory(
        FakeUserSetup(
            subj="bob",
            email="bob@x.test",
            noun=Noun(value="Bob", pronoun=Pronouns.HE),
            skills=Skills(
                martial_arts=Skill(name="Martial Arts", tnl=4.0),
                evasion=Skill(name="Evasion", tnl=4.0),
            ),
        ),
    )
    await alice.recv()

    # bob takes a swing at alice (jerk!)
    async with asyncio.timeout(0.25):
        await bob.send("att alice")
        golden("bob", await bob.recv())
        golden("alice", await alice.recv())

    # bob can't move while attacking
    async with asyncio.timeout(0.25):
        await bob.send("west")
        golden("bob", await bob.recv())

    # alice fights back!
    async with asyncio.timeout(0.25):
        await alice.send("att bob")
        golden("alice", await alice.recv())
        golden("bob", await bob.recv())

    # bob hits alice!
    # alice goes into shock!
    async with asyncio.timeout(get_melee_delay() + 0.25):
        golden("bob", await bob.recv())
        golden("alice", await alice.recv())

    # alice cant move while in shock
    async with asyncio.timeout(0.25):
        await alice.send("west")
        golden("alice", await alice.recv())

    # alice dies. bob and alice see it.
    async with asyncio.timeout(5):
        golden("bob", await bob.recv())
        golden("alice", await alice.recv())
    # alice cant move, she's dead
    async with asyncio.timeout(0.25):
        await alice.send("west")
        golden("alice", await alice.recv())

    # they dont see anything else
    for cli in (alice, bob):
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.25):
                await cli.recv()

    # todo: test stuns
