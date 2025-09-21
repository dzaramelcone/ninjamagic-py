import asyncio
import pytest

from tests.conftest import ClientFactory, GoldenChecker


@pytest.mark.asyncio
async def test_solo_client(
    golden: GoldenChecker, client_factory: ClientFactory
) -> None:
    alice = await client_factory(subj="alice", email="alice@x.test")
    async with asyncio.timeout(1):
        golden(await alice.recv())

        await alice.send("asdok")
        golden(await alice.recv())

        await alice.send("'")
        golden(await alice.recv())

        await alice.send("'hi!")
        golden(await alice.recv())


@pytest.mark.asyncio
async def test_chat(golden, client_factory):
    alice = await client_factory(subj="alice", email="alice@x.test")
    bob = await client_factory(subj="bob", email="bob@x.test")
    async with asyncio.timeout(1):
        golden(await alice.recv())
        golden(await bob.recv())

        await alice.send("say hi")
        golden(await alice.recv())
        golden(await bob.recv())

        await bob.send("'hello")
        golden(await alice.recv())
        golden(await bob.recv())
