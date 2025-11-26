import asyncio
import json
import pathlib
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any

import httpx
import pytest
import pytest_asyncio
import websockets
from google.protobuf.json_format import MessageToDict
from websockets.asyncio.client import ClientConnection

from ninjamagic.gen.messages_pb2 import Packet
from tests.util import FakeUserSetup

BASE_HTTP_URL = "http://localhost:8000"
BASE_WS_URL = "ws://localhost:8000"

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


@pytest.fixture
def golden_json(
    request: pytest.FixtureRequest, golden_update: bool
) -> Callable[[Any], None]:
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
def golden(
    request: pytest.FixtureRequest, golden_update: bool
) -> Callable[[str, str | bytes], None]:
    """
    Write-or-compare test artifacts (goldens).

    Usage:
        golden(await alice.recv())

    Behavior:
      - str: must be JSON; re-serialized deterministic pretty JSON.
      - bytes: always dump hex as first line (after client header), then:
          1) Protobuf Packet -> pretty JSON
          2) UTF-8 JSON -> pretty JSON
          3) fallback: just hex
    """
    base_dir = pathlib.Path(__file__).parent / "goldens" / request.node.name
    ctr = 0

    def _pp_json(obj: Any) -> str:
        return json.dumps(obj, indent=2, sort_keys=True) + "\n"

    def _decode_bytes(b: bytes) -> str:
        hex_line = b.hex()
        parts = [hex_line]

        try:
            pkt = Packet()
            pkt.ParseFromString(b)
            as_dict = MessageToDict(
                pkt,
                preserving_proto_field_name=True,
                use_integers_for_enums=False,
            )
            parts.append(_pp_json(as_dict))
        except Exception:
            try:
                maybe = json.loads(b.decode("utf-8"))
                parts.append(_pp_json(maybe))
            except Exception:
                pass

        return "\n".join(parts).rstrip() + "\n"

    def _golden(client: str, data: str | bytes) -> None:
        nonlocal ctr

        header = f"# client: {client}\n# len: {len(data)} B\n"
        if isinstance(data, str):
            payload = json.loads(data)
            assert payload, "Did not receive valid JSON data!"
            rendered = header + _pp_json(payload)
        else:
            rendered = header + _decode_bytes(data)

        g_path = base_dir / f"{request.node.name}-{ctr}.out"
        ctr += 1

        if golden_update or not g_path.exists():
            g_path.parent.mkdir(parents=True, exist_ok=True)
            g_path.write_text(rendered)
            return

        expected = g_path.read_text()
        assert rendered == expected

    return _golden


@pytest_asyncio.fixture(scope="function")
async def client_factory() -> ClientFactory:
    """
    Yields:
        An async function `_create_session(email: str, subj: str, setup: dict | None = None)`
        that returns a new authenticated WebSocket client with optional component overrides.
    """
    active_connections: list[ClientConnection] = []

    async def _create_session(
        setup: FakeUserSetup, discard_init: bool = True
    ) -> ClientConnection:
        async with (
            asyncio.timeout(0.25),
            httpx.AsyncClient(base_url=BASE_HTTP_URL) as http_client,
        ):
            try:
                auth_response = await http_client.post(
                    "/auth/local", json=asdict(setup)
                )
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
