import asyncio
import json
import pathlib
from typing import AsyncGenerator, Callable, Coroutine
import httpx
import pytest
import pytest_asyncio
import websockets
from websockets.asyncio.client import ClientConnection

BASE_HTTP_URL = "http://localhost:8000"
BASE_WS_URL = "ws://localhost:8000"
GoldenChecker = Callable[[str], None]
ClientFactory = Callable[[str, str], Coroutine[any, any, ClientConnection]]


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
def golden(
    request: pytest.FixtureRequest, golden_update: bool
) -> Callable[[str], None]:
    base_dir = pathlib.Path(__file__).parent / "goldens"
    ctr = 0

    def _golden(data: str) -> None:
        data = json.loads(data)
        assert data, "Did not receive valid json data!"
        nonlocal ctr
        g_path = base_dir / f"{request.node.name}-{ctr}.json"
        ctr += 1
        if golden_update or not g_path.exists():
            g_path.parent.mkdir(parents=True, exist_ok=True)
            g_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
            return

        expected = json.loads(g_path.read_text())
        assert data == expected

    return _golden


@pytest_asyncio.fixture(scope="function")
async def client_factory() -> AsyncGenerator[
    Callable[[str, str], Coroutine[any, any, ClientConnection]],
    None,
]:
    """
    A pytest fixture that provides a "factory" for creating authenticated WebSocket clients.

    Instead of yielding a client directly, it yields an async function that can be
    called to produce a new, authenticated WebSocket session. This allows a single
    test to manage multiple concurrent connections.

    The fixture is responsible for tracking all created connections and ensuring
    they are all closed cleanly at the end of the test.

    Yields:
        An async function `_create_session(email: str, subj: str)` that,
        when awaited, returns a new authenticated WebSocket client.
    """
    active_connections: list[ClientConnection] = []

    async def _create_session(email: str, subj: str) -> ClientConnection:
        """
        Creates a single authenticated WebSocket session.
        1. Authenticates over HTTP with the provided email and subject.
        2. Establishes a WebSocket connection using the resulting session cookie.
        3. Tracks the connection for later cleanup.
        """
        async with httpx.AsyncClient(base_url=BASE_HTTP_URL) as http_client:
            try:
                auth_params = {"email": email, "subj": subj}
                auth_response = await http_client.get("/auth/local", params=auth_params)

                session_cookie = auth_response.cookies.get("session")
                if not session_cookie:
                    pytest.fail(
                        f"The 'session' cookie was not found for user '{email}'. "
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
            # We connect directly instead of using `async with` because the fixture
            # needs to manage the connection's lifecycle across the test's duration.
            websocket = await websockets.connect(
                uri=websocket_uri, additional_headers=connection_headers
            )
            # Add the new connection to our list for cleanup.
            active_connections.append(websocket)
            return websocket

        except websockets.exceptions.InvalidStatusCode as e:
            pytest.fail(
                f"WebSocket connection for '{email}' failed with status {e.status_code}. "
                "This likely means the session cookie was rejected by the server."
            )
        except ConnectionRefusedError:
            pytest.fail(
                f"WebSocket connection for '{email}' was refused. "
                "Please ensure your FastAPI server is running and accessible."
            )

    # Yield the factory function to the test.
    yield _create_session

    # --- Teardown ---
    # This code runs after the test function has completed.
    # We create a list of closing tasks to run them concurrently.
    close_tasks = [conn.close() for conn in active_connections]
    if close_tasks:
        await asyncio.gather(*close_tasks)
