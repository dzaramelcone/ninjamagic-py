"""MCP server for ninjamagic game interaction.

Connects to the game on startup and exposes tools for viewing state,
sending commands, and reading messages. Writes new messages to a
notification file for hook-based push notifications.
"""

import asyncio
import logging
import os
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP

from ninjamagic.ai.client import Client, PROD_BASE_URL, PROD_WS_URL, load_session_cookie, PlayerSetup
from ninjamagic.component import Noun


log = logging.getLogger(__name__)

# Local dev server
LOCAL_BASE_URL = "http://localhost:8000"
LOCAL_WS_URL = "ws://localhost:8000"

# File where new messages are written for the hook to read
NOTIFICATION_FILE = os.path.expanduser("~/.ninjamagic_notifications")


@dataclass
class GameConnection:
    """Holds the game client and message buffer."""
    client: Client
    messages: deque  # bounded buffer of recent messages
    seen_messages: set = field(default_factory=set)  # track what we've notified about


def write_notification(message: str) -> None:
    """Append a message to the notification file."""
    with open(NOTIFICATION_FILE, "a") as f:
        f.write(message + "\n")


async def message_watcher(game: GameConnection) -> None:
    """Background task that watches for new messages and writes to notification file."""
    while True:
        await asyncio.sleep(1.0)  # Check every second

        # Get current messages
        current = set(game.client.state.messages)

        # Find new ones
        new_messages = current - game.seen_messages

        for msg in new_messages:
            # Only notify about messages from others (not our own "You say" messages)
            if not msg.startswith("You "):
                write_notification(f"[GAME] {msg}")
            game.seen_messages.add(msg)
            game.messages.append(msg)


# Will be set during lifespan
_game: GameConnection | None = None
_watcher_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Connect to ninjamagic on startup."""
    global _game, _watcher_task

    client = Client(base_url=PROD_BASE_URL, ws_url=PROD_WS_URL)

    # Try cached session first
    cached = load_session_cookie()
    if cached:
        client._session_cookie = cached
        try:
            await client._connect_ws()
            await asyncio.sleep(0.5)
            if client.state.entities:
                # Connected successfully
                _game = GameConnection(
                    client=client,
                    messages=deque(maxlen=100),
                    seen_messages=set(client.state.messages)  # Don't notify about existing messages
                )

                # Start background watcher
                _watcher_task = asyncio.create_task(message_watcher(_game))

                yield _game

                # Cleanup
                _watcher_task.cancel()
                try:
                    await _watcher_task
                except asyncio.CancelledError:
                    pass
                await client.disconnect()
                return
        except Exception:
            pass

    # No valid cached session - need fresh OAuth
    _game = None
    yield None


mcp = FastMCP(
    name="ninjamagic",
    instructions="Play Dzara's game as Vigil. Use view to see the world, send to act, messages to read recent game output.",
    lifespan=lifespan,
)


async def ensure_connected() -> bool:
    """Ensure websocket is connected, reconnecting if needed. Returns True if connected."""
    if _game is None:
        return False

    # Check if websocket is still open
    ws = _game.client._ws
    if ws and ws.close_code is None:
        return True

    # Try to reconnect
    log.info("WebSocket disconnected, attempting reconnect...")
    try:
        await _game.client._connect_ws()
        await asyncio.sleep(0.5)
        if _game.client.state.entities:
            log.info("Reconnected successfully.")
            # Re-seed seen messages to avoid duplicate notifications
            _game.seen_messages = set(_game.client.state.messages)
            return True
    except Exception as e:
        log.warning("Reconnect failed: %s", e)

    return False


@mcp.tool()
async def view() -> str:
    """See the current game state - entities, position, health, time."""
    if _game is None:
        return "Not connected to ninjamagic. Run `connect_to_prod()` in Python first to establish session."

    if not await ensure_connected():
        return "Disconnected from game server. Could not reconnect."

    return _game.client.state.render_prompt()


@mcp.tool()
async def send(command: str) -> str:
    """Send a command to the game. Examples: 'n' (north), 'say Hello', 'forage', 'look'."""
    if _game is None:
        return "Not connected to ninjamagic."

    if not await ensure_connected():
        return "Disconnected from game server. Could not reconnect."

    await _game.client.send(command)
    await asyncio.sleep(0.3)  # Wait for response

    # Capture any new messages
    new_msgs = list(_game.client.state.messages)
    for msg in new_msgs:
        if msg not in _game.messages:
            _game.messages.append(msg)

    # Return current state
    return _game.client.state.render_prompt()


@mcp.tool()
def messages(count: int = 10) -> str:
    """Get recent game messages."""
    if _game is None:
        return "Not connected to ninjamagic."

    # Get messages from both buffer and client state
    all_msgs = list(_game.messages) + list(_game.client.state.messages)
    # Dedupe while preserving order
    seen = set()
    unique = []
    for m in all_msgs:
        if m not in seen:
            seen.add(m)
            unique.append(m)

    recent = unique[-count:] if len(unique) > count else unique
    if not recent:
        return "No messages yet."
    return "\n".join(recent)


@mcp.tool()
async def status() -> str:
    """Check connection status."""
    if _game is None:
        return "Disconnected. Need to establish session first."

    ws = _game.client._ws
    if not ws or ws.close_code is not None:
        # Try to reconnect
        if await ensure_connected():
            return "Reconnected as Vigil."
        return "WebSocket disconnected. Reconnect failed."

    return "Connected as Vigil."


@mcp.tool()
def skills() -> str:
    """See your skills and experience progress."""
    if _game is None:
        return "Not connected to ninjamagic."

    if not _game.client.state.skills:
        return "No skills yet."

    lines = ["=== SKILLS ==="]
    for name, skill in sorted(_game.client.state.skills.items()):
        # tnl is progress to next level (0.0 to 1.0)
        progress = int(skill.tnl * 100)
        lines.append(f"  {name}: rank {skill.rank} ({progress}% to next)")

    return "\n".join(lines)


@mcp.tool()
async def connect_local() -> str:
    """Connect to localhost:8000 for local playtesting. Requires server running locally."""
    global _game, _watcher_task

    # Disconnect existing connection
    if _game is not None:
        if _watcher_task:
            _watcher_task.cancel()
            try:
                await _watcher_task
            except asyncio.CancelledError:
                pass
        await _game.client.disconnect()
        _game = None
        _watcher_task = None

    # Connect to local server
    client = Client(base_url=LOCAL_BASE_URL, ws_url=LOCAL_WS_URL)
    try:
        await client.connect(PlayerSetup(noun=Noun(value="Vigil")))
        _game = GameConnection(
            client=client,
            messages=deque(maxlen=100),
            seen_messages=set(client.state.messages),
        )
        _watcher_task = asyncio.create_task(message_watcher(_game))
        return "Connected to localhost:8000 as Vigil."
    except Exception as e:
        return f"Failed to connect to localhost: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
