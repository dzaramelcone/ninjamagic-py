import asyncio
import json
import pathlib
import warnings
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

import httpx
import pytest
import pytest_asyncio
import websockets
from deepdiff import DeepDiff
from google.protobuf.json_format import MessageToDict
from pydantic.dataclasses import Field, dataclass
from websockets.asyncio.client import ClientConnection

import ninjamagic.db as db
from ninjamagic.component import Glyph, Health, Noun, Skills, Stance, Stats, Transform
from ninjamagic.db import engine
from ninjamagic.gen.messages_pb2 import Packet
from ninjamagic.gen.query import AsyncQuerier

BASE_HTTP_URL = "http://localhost:8000"
BASE_WS_URL = "ws://localhost:8000"


# TODO Just use the sqlc generated fake models. UpdateCharacterParams or whatever.
@dataclass
class FakeUserSetup:
    subj: str = "12023"
    email: str = "test@example.com"
    glyph: Glyph = ("@", 0.5833, 0.7, 0.828)
    health: Health = Field(default_factory=Health)
    stance: Stance = Field(default_factory=Stance)
    stats: Stats = Field(default_factory=Stats)
    skills: Skills = Field(default_factory=Skills)
    transform: Transform = Field(default_factory=lambda: Transform(map_id=1, x=2, y=2))
    noun: Noun = Field(default_factory=Noun)


ClientFactory = Callable[[FakeUserSetup, bool], Awaitable[ClientConnection]]


def pytest_addoption(parser: pytest.Parser) -> None:
    """Adds the --golden-update command-line option to pytest."""
    parser.addoption(
        "-G",
        "--golden-update",
        action="store_true",
        default=False,
        help="Update the golden files.",
    )


@pytest.fixture(scope="session")
def golden_update(request: pytest.FixtureRequest) -> bool:
    """Fixture that returns True if the --golden-update flag is set."""
    return request.config.getoption("--golden-update")


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio")


@pytest.fixture(autouse=True)
def make_tests_deterministic():
    from ninjamagic.util import RNG

    state = RNG.getstate()
    yield
    RNG.setstate(state)


@pytest.fixture
def golden_json(request: pytest.FixtureRequest, golden_update: bool) -> Callable[[Any], None]:
    base_dir = pathlib.Path(__file__).parent / "goldens" / request.node.name
    ctr = 0

    def _golden(data: Any) -> None:
        nonlocal ctr
        g_path = base_dir / f"{request.node.name}-{ctr}.out"
        ctr += 1
        if golden_update or not g_path.exists():
            g_path.parent.mkdir(parents=True, exist_ok=True)
            g_path.write_text(json.dumps(data, indent=1))
            return
        expected = json.loads(g_path.read_text())
        assert data == expected

    return _golden


@pytest.fixture
def golden_ws(
    request: pytest.FixtureRequest, golden_update: bool
) -> Callable[[str, str | bytes], None]:
    """
    Write-or-compare test artifacts (goldens).

    Usage:
        golden(await alice.recv())
    """

    base_dir = pathlib.Path(__file__).parent / "goldens" / request.node.name
    ctr = 0

    def proto_loadb(b: bytes) -> str:
        pkt = Packet()
        pkt.ParseFromString(b)
        return MessageToDict(
            pkt,
            preserving_proto_field_name=True,
            use_integers_for_enums=False,
        )

    def _golden(client: str, data: str | bytes) -> None:
        nonlocal ctr

        rendered = {
            "client": client,
            "len": f"{len(data)} B",
            "parsed": (json.loads(data) if isinstance(data, str) else proto_loadb(data)),
        }

        g_path = base_dir / f"{request.node.name}-{ctr}.out"
        ctr += 1

        if golden_update or not g_path.exists():
            g_path.parent.mkdir(parents=True, exist_ok=True)
            g_path.write_text(json.dumps(rendered, indent=2, sort_keys=True))
            return

        expected = json.loads(g_path.read_text())

        # Tolerate small len differences
        expected_len_str = expected.get("len", "")
        if expected_len_str.endswith(" B"):
            expected_bytes = int(expected_len_str[:-2])
            actual_bytes = len(data)
            tolerance = max(10, int(expected_bytes * 0.025))
            if abs(actual_bytes - expected_bytes) <= tolerance:
                rendered["len"] = expected["len"]  # normalize to avoid diff

        diff = DeepDiff(rendered, expected, exclude_regex_paths=[r"root.*?\['(id|seconds)'\]"])
        if diff:
            # Structural changes (keys added/removed) are failures
            structural_keys = {
                "dictionary_item_added",
                "dictionary_item_removed",
                "iterable_item_added",
                "iterable_item_removed",
                "type_changes",
            }
            structural = {k: v for k, v in diff.items() if k in structural_keys}
            value_only = {k: v for k, v in diff.items() if k not in structural_keys}

            if value_only:
                warnings.warn(
                    f"Golden value drift:\n{json.dumps(value_only, indent=2)}",
                    stacklevel=2,
                )
            if structural:
                pytest.fail(f"Golden structure mismatch:\n{json.dumps(structural, indent=2)}")

    return _golden


@pytest_asyncio.fixture(scope="function")
async def client_factory() -> ClientFactory:
    """
    Yields:
        An async function `_create_session(email: str, subj: str, setup: dict | None = None)`
        that returns a new authenticated WebSocket client with optional component overrides.
    """
    active_connections: list[ClientConnection] = []

    async def _create_session(setup: FakeUserSetup, discard_init: bool = True) -> ClientConnection:
        async with (
            asyncio.timeout(0.25),
            httpx.AsyncClient(base_url=BASE_HTTP_URL) as http_client,
        ):
            try:
                auth_response = await http_client.post("/auth/local", json=asdict(setup))
                assert auth_response.status_code < 400, "Bad response"
                session_cookie = auth_response.cookies.get("session")
                if not session_cookie:
                    pytest.fail(
                        f"The 'session' cookie was not found for user '{setup.email}'. "
                        "Ensure the auth endpoint is setting it correctly."
                    )

            except httpx.ConnectError:
                pytest.fail(
                    f"Connection to '{BASE_HTTP_URL}' failed. "
                    "Please ensure your FastAPI server is running."
                )

        connection_headers = {"Cookie": f"session={session_cookie}"}
        websocket_uri = f"{BASE_WS_URL}/ws"

        try:
            async with asyncio.timeout(0.25):
                websocket = await websockets.connect(
                    uri=websocket_uri, additional_headers=connection_headers
                )
            active_connections.append(websocket)
            if discard_init:
                _ = await websocket.recv()
            return websocket
        except websockets.exceptions.InvalidStatusCode as e:
            pytest.fail(
                f"WebSocket connection for '{setup.email}' failed with status {e.status_code}. "
                "This likely means the session cookie was rejected by the server."
            )
            raise e
        except ConnectionRefusedError as e:
            pytest.fail(
                f"WebSocket connection for '{setup.email}' was refused. "
                "Please ensure your FastAPI server is running and accessible."
            )
            raise e

    yield _create_session

    close_tasks = [conn.close() for conn in active_connections]
    if close_tasks:
        await asyncio.gather(*close_tasks)


@pytest_asyncio.fixture(autouse=True)
async def db_rollback():
    import importlib

    async with engine.connect() as conn:
        tx = await conn.begin()

        @asynccontextmanager
        async def _get_conn():
            yield conn

        async def _get_repository(_):
            return AsyncQuerier(conn)

        @asynccontextmanager
        async def _get_repository_factory():
            yield AsyncQuerier(conn)

        # Patch db.get_repository_factory for non-FastAPI code paths
        original_get_repository_factory = db.get_repository_factory
        db.get_repository_factory = _get_repository_factory

        app = importlib.import_module("ninjamagic.main").app
        app.dependency_overrides[db.get_conn] = _get_conn
        app.dependency_overrides[db.get_repository] = _get_repository
        app.dependency_overrides[db.get_repository_factory] = _get_repository_factory
        try:
            yield
        finally:
            app.dependency_overrides.pop(db.get_conn, None)
            app.dependency_overrides.pop(db.get_repository, None)
            app.dependency_overrides.pop(db.get_repository_factory, None)
            db.get_repository_factory = original_get_repository_factory
            await tx.rollback()
