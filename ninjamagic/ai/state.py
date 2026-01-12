"""Game state tracking for AI player."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Entity:
    """An entity the client knows about."""

    id: int
    glyph: str = "?"
    h: float = 0.0
    s: float = 0.0
    v: float = 0.0
    noun: str = ""
    x: int = 0
    y: int = 0
    map_id: int = 0
    health_pct: float = 1.0
    stress_pct: float = 0.0
    stance: str = ""
    condition: str = ""


@dataclass
class Skill:
    """A skill and its progress."""

    name: str
    rank: int = 0
    tnl: float = 0.0


@dataclass
class GameState:
    """Complete game state as known to the client."""

    # Tiles: (map_id, top, left) -> 16x16 bytearray
    tiles: dict[tuple[int, int, int], bytearray] = field(default_factory=dict)

    # Chipset: (tile_id, map_id) -> (glyph_char, h, s, v, a)
    chipset: dict[tuple[int, int], tuple[str, float, float, float, float]] = field(
        default_factory=dict
    )

    # Entities by id (id=0 is self)
    entities: dict[int, Entity] = field(default_factory=dict)

    # Skills
    skills: dict[str, Skill] = field(default_factory=dict)

    # Game time
    game_time: datetime | None = None

    # Current prompt (if any)
    prompt: str | None = None

    # Recent messages
    messages: deque[str] = field(default_factory=lambda: deque(maxlen=50))

    # My position (convenience)
    @property
    def me(self) -> Entity:
        if 0 not in self.entities:
            self.entities[0] = Entity(id=0, glyph="@")
        return self.entities[0]

    def get_tile_glyph(self, map_id: int, y: int, x: int) -> str:
        """Get the glyph at a specific world coordinate."""
        top = (y // 16) * 16
        left = (x // 16) * 16
        key = (map_id, top, left)
        if key not in self.tiles:
            return " "
        tile = self.tiles[key]
        local_y = y - top
        local_x = x - left
        idx = local_y * 16 + local_x
        if idx < 0 or idx >= len(tile):
            return " "
        tile_id = tile[idx]
        chip_key = (tile_id, map_id)
        if chip_key in self.chipset:
            return self.chipset[chip_key][0]
        # Fallback defaults
        defaults = {0: " ", 1: ".", 2: "#", 3: "~", 4: '"', 5: "%"}
        return defaults.get(tile_id, "?")

    def render_view(self, radius: int = 8) -> str:
        """Render ASCII view centered on self."""
        me = self.me
        lines = []

        # Build entity position lookup
        entity_at: dict[tuple[int, int, int], Entity] = {}
        for eid, ent in self.entities.items():
            if eid != 0 and ent.map_id == me.map_id:
                entity_at[(ent.map_id, ent.y, ent.x)] = ent

        for dy in range(-radius, radius + 1):
            row = []
            for dx in range(-radius, radius + 1):
                wy = me.y + dy
                wx = me.x + dx
                if dy == 0 and dx == 0:
                    row.append(me.glyph)
                elif (me.map_id, wy, wx) in entity_at:
                    row.append(entity_at[(me.map_id, wy, wx)].glyph)
                else:
                    row.append(self.get_tile_glyph(me.map_id, wy, wx))
            lines.append("".join(row))

        return "\n".join(lines)

    def render_status(self) -> str:
        """Render status line."""
        me = self.me
        parts = [
            f"HP: {me.health_pct * 100:.0f}%",
            f"Stress: {me.stress_pct * 100:.0f}%",
        ]
        if me.stance:
            parts.append(f"Stance: {me.stance}")
        if me.condition:
            parts.append(f"Condition: {me.condition}")
        if self.game_time:
            parts.append(f"Time: {self.game_time.strftime('%H:%M')}")
        return " | ".join(parts)

    def render_prompt(self) -> str:
        """Render the full prompt for an LLM."""
        lines = []

        # Map view
        lines.append("=== MAP ===")
        lines.append(self.render_view())
        lines.append("")

        # Status
        lines.append("=== STATUS ===")
        lines.append(self.render_status())
        lines.append("")

        # Nearby entities
        me = self.me
        nearby = []
        for eid, ent in self.entities.items():
            if eid == 0:
                continue
            if ent.map_id != me.map_id:
                continue
            dist = abs(ent.y - me.y) + abs(ent.x - me.x)
            if dist <= 10 and ent.noun:
                dy = ent.y - me.y
                dx = ent.x - me.x
                direction = self._direction(dy, dx)
                nearby.append(f"  {ent.glyph} {ent.noun} ({direction}, {dist} away)")
        if nearby:
            lines.append("=== NEARBY ===")
            lines.extend(nearby)
            lines.append("")

        # Recent messages
        if self.messages:
            lines.append("=== RECENT ===")
            for msg in list(self.messages)[-5:]:
                lines.append(f"  {msg}")
            lines.append("")

        # Current prompt
        if self.prompt:
            lines.append("=== PROMPT ===")
            lines.append(f"  {self.prompt}")
            lines.append("")

        return "\n".join(lines)

    def _direction(self, dy: int, dx: int) -> str:
        if dy < 0 and dx == 0:
            return "N"
        if dy < 0 and dx > 0:
            return "NE"
        if dy == 0 and dx > 0:
            return "E"
        if dy > 0 and dx > 0:
            return "SE"
        if dy > 0 and dx == 0:
            return "S"
        if dy > 0 and dx < 0:
            return "SW"
        if dy == 0 and dx < 0:
            return "W"
        if dy < 0 and dx < 0:
            return "NW"
        return "here"
