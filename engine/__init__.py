
"""
MHN ARCADE V3 - Game Engine

Public interface for the complete V3 engine.
Provides centralized access to sessions, lobbies,
game registry, catalog, runner, and game handlers.
"""

# =========================================================
# CORE
# =========================================================

from .core import (
    GameSession,
    PlayerStatus,
    SessionError,
    SessionManager,
    SessionPlayer,
    SessionStatus,
)

# =========================================================
# LOBBY
# =========================================================

from .lobby import LobbyManager

# =========================================================
# REGISTRY
# =========================================================

from .registry import (
    GameDefinition,
    GameMode,
    GameRegistry,
    RegistryError,
)

# =========================================================
# CATALOG
# =========================================================

from .catalog import (
    DEFAULT_GAMES,
    build_default_registry,
    get_catalog_summary,
)

# =========================================================
# RUNNER
# =========================================================

from .runner import (
    GameLaunch,
    GameRunner,
    RunnerError,
)

# =========================================================
# GAME HANDLERS
# =========================================================

from .games import (
    Elimination,
    MusicalRoulette,
    MusicalRouletteError,
    RouletteResult,
)

# =========================================================
# PUBLIC API
# =========================================================

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

    # Catalog
    "DEFAULT_GAMES",
    "build_default_registry",
    "get_catalog_summary",

    # Runner
    "GameLaunch",
    "GameRunner",
    "RunnerError",

    # Game Handlers
    "Elimination",
    "MusicalRoulette",
    "MusicalRouletteError",
    "RouletteResult",
]
