
"""
MHN ARCADE V3 - Game Engine

Public engine interface.
"""

from .core import (
    GameSession,
    PlayerStatus,
    SessionError,
    SessionManager,
    SessionPlayer,
    SessionStatus,
)

from .lobby import LobbyManager

from .registry import (
    GameDefinition,
    GameMode,
    GameRegistry,
    RegistryError,
)


__all__ = [
    # Core
    "GameSession",
    "PlayerStatus",
    "SessionError",
    "SessionManager",
    "SessionPlayer",
    "SessionStatus",

    # Lobby
    "LobbyManager",

    # Registry
    "GameDefinition",
    "GameMode",
    "GameRegistry",
    "RegistryError",
]
