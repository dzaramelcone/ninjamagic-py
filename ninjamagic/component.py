from dataclasses import dataclass as component
from fastapi import WebSocket


EntityId = int
ActionId = int
Connection = WebSocket
Lag = float
OwnerId = int


@component(slots=True, kw_only=True)
class Position:
    mid: EntityId
    x: int
    y: int
