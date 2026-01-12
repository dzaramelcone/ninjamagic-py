"""WebSocket client for AI player."""

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone

import httpx
import websockets
from pydantic.dataclasses import Field, dataclass
from websockets.asyncio.client import ClientConnection

from ninjamagic.ai.state import Entity, GameState, Skill
from ninjamagic.component import Glyph, Health, Noun, Skills, Stance, Stats, Transform
from ninjamagic.gen.messages_pb2 import Packet


@dataclass
class PlayerSetup:
    """Configuration for creating/loading a player."""

    subj: str = "ai-player-001"
    email: str = "ai@ninjamagic.local"
    glyph: Glyph = ("@", 0.5833, 0.7, 0.828)
    health: Health = Field(default_factory=Health)
    stance: Stance = Field(default_factory=Stance)
    stats: Stats = Field(default_factory=Stats)
    skills: Skills = Field(default_factory=Skills)
    transform: Transform = Field(default_factory=lambda: Transform(map_id=1, x=4, y=8))
    noun: Noun = Field(default_factory=lambda: Noun(value="seeker"))


class Client:
    """WebSocket client that maintains game state."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        ws_url: str = "ws://localhost:8000",
    ):
        self.base_url = base_url
        self.ws_url = ws_url
        self.state = GameState()
        self._ws: ClientConnection | None = None
        self._recv_task: asyncio.Task | None = None

    async def connect(self, setup: PlayerSetup | None = None) -> None:
        """Connect to the game server."""
        setup = setup or PlayerSetup()

        # Authenticate
        async with httpx.AsyncClient(base_url=self.base_url) as http:
            response = await http.post("/auth/local", json=asdict(setup))
            response.raise_for_status()
            session_cookie = response.cookies.get("session")
            if not session_cookie:
                raise RuntimeError("No session cookie received")

        # Connect websocket
        headers = {"Cookie": f"session={session_cookie}"}
        self._ws = await websockets.connect(
            f"{self.ws_url}/ws", additional_headers=headers
        )

        # Start receiving in background
        self._recv_task = asyncio.create_task(self._recv_loop())

        # Wait a bit for initial state
        await asyncio.sleep(0.1)

    async def disconnect(self) -> None:
        """Disconnect from the game server."""
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()

    async def send(self, command: str) -> None:
        """Send a command to the server."""
        if not self._ws:
            raise RuntimeError("Not connected")
        await self._ws.send(command)

    async def wait_for_messages(self, timeout: float = 0.5) -> None:
        """Wait for messages to arrive."""
        await asyncio.sleep(timeout)

    async def _recv_loop(self) -> None:
        """Background loop receiving packets."""
        if not self._ws:
            return
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    self._handle_packet(message)
        except websockets.exceptions.ConnectionClosed:
            pass

    def _handle_packet(self, data: bytes) -> None:
        """Parse and apply a packet to game state."""
        packet = Packet()
        packet.ParseFromString(data)

        for kind in packet.envelope:
            which = kind.WhichOneof("body")
            if which == "msg":
                self.state.messages.append(kind.msg.text)
            elif which == "pos":
                self._update_entity_pos(kind.pos)
            elif which == "chip":
                self._update_chip(kind.chip)
            elif which == "tile":
                self._update_tile(kind.tile)
            elif which == "glyph":
                self._update_entity_glyph(kind.glyph)
            elif which == "noun":
                self._update_entity_noun(kind.noun)
            elif which == "health":
                self._update_entity_health(kind.health)
            elif which == "stance":
                self._update_entity_stance(kind.stance)
            elif which == "condition":
                self._update_entity_condition(kind.condition)
            elif which == "skill":
                self._update_skill(kind.skill)
            elif which == "datetime":
                self._update_datetime(kind.datetime)
            elif which == "prompt":
                self.state.prompt = kind.prompt.text if kind.prompt.text else None

    def _get_entity(self, eid: int) -> Entity:
        if eid not in self.state.entities:
            self.state.entities[eid] = Entity(id=eid)
        return self.state.entities[eid]

    def _update_entity_pos(self, pos) -> None:
        ent = self._get_entity(pos.id)
        ent.map_id = pos.map_id
        ent.x = pos.x
        ent.y = pos.y

    def _update_chip(self, chip) -> None:
        # Convert glyph codepoint to character
        glyph_char = chr(chip.glyph) if chip.glyph else " "
        self.state.chipset[(chip.id, chip.map_id)] = (
            glyph_char,
            chip.h,
            chip.s,
            chip.v,
            chip.a,
        )

    def _update_tile(self, tile) -> None:
        key = (tile.map_id, tile.top, tile.left)
        self.state.tiles[key] = bytearray(tile.data)

    def _update_entity_glyph(self, glyph) -> None:
        ent = self._get_entity(glyph.id)
        ent.glyph = glyph.glyph
        ent.h = glyph.h
        ent.s = glyph.s
        ent.v = glyph.v

    def _update_entity_noun(self, noun) -> None:
        ent = self._get_entity(noun.id)
        ent.noun = noun.text

    def _update_entity_health(self, health) -> None:
        ent = self._get_entity(health.id)
        ent.health_pct = health.pct
        ent.stress_pct = health.stress_pct

    def _update_entity_stance(self, stance) -> None:
        ent = self._get_entity(stance.id)
        ent.stance = stance.text

    def _update_entity_condition(self, condition) -> None:
        ent = self._get_entity(condition.id)
        ent.condition = condition.text

    def _update_skill(self, skill) -> None:
        self.state.skills[skill.name] = Skill(
            name=skill.name, rank=skill.rank, tnl=skill.tnl
        )

    def _update_datetime(self, dt) -> None:
        self.state.game_time = datetime.fromtimestamp(dt.seconds, tz=timezone.utc)


async def play_interactive() -> None:
    """Interactive REPL for testing the client."""
    client = Client()

    print("Connecting...")
    await client.connect()
    print("Connected!")
    print()

    # Initial view
    await client.wait_for_messages(0.5)
    print(client.state.render_prompt())

    try:
        while True:
            command = input("> ").strip()
            if command.lower() in ("quit", "exit", "q"):
                break
            if command.lower() == "look":
                print(client.state.render_prompt())
                continue
            if command:
                await client.send(command)
                await client.wait_for_messages(0.3)
                print(client.state.render_prompt())
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        await client.disconnect()
        print("\nDisconnected.")


if __name__ == "__main__":
    asyncio.run(play_interactive())
