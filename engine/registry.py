
"""
MHN ARCADE V3 - Game Registry

Central registry for all game definitions.
Keeps game metadata separate from Discord and game mechanics.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# =========================================================
# ENUMS
# =========================================================

class GameMode(str, Enum):
    SINGLE_PLAYER = "single_player"
    MULTIPLAYER = "multiplayer"


# =========================================================
# ERRORS
# =========================================================

class RegistryError(Exception):
    """Raised when a game registry operation is invalid."""


# =========================================================
# GAME DEFINITION
# =========================================================

@dataclass(frozen=True)
class GameDefinition:
    """
    Describes a game supported by MHN ARCADE V3.

    This class contains metadata only.
    Game mechanics are implemented separately.
    """

    game_id: str
    name_en: str
    name_ar: str
    mode: GameMode

    min_players: int = 1
    max_players: int = 1

    description_en: str = ""
    description_ar: str = ""

    tags: tuple[str, ...] = field(default_factory=tuple)

    handler_factory: Callable[..., Any] | None = field(
        default=None,
        compare=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        game_id = self.game_id.strip().lower()

        if not game_id:
            raise RegistryError("Game ID cannot be empty.")

        if not re.fullmatch(r"[a-z0-9_-]+", game_id):
            raise RegistryError(
                "Game ID may contain only letters, numbers, "
                "underscores, and hyphens."
            )

        object.__setattr__(self, "game_id", game_id)

        if not self.name_en.strip():
            raise RegistryError("English game name cannot be empty.")

        if not self.name_ar.strip():
            raise RegistryError("Arabic game name cannot be empty.")

        if not isinstance(self.mode, GameMode):
            raise RegistryError("Invalid game mode.")

        if (
            not isinstance(self.min_players, int)
            or isinstance(self.min_players, bool)
            or not isinstance(self.max_players, int)
            or isinstance(self.max_players, bool)
        ):
            raise RegistryError("Player limits must be integers.")

        if self.min_players < 1:
            raise RegistryError("Minimum players must be at least 1.")

        if self.max_players < self.min_players:
            raise RegistryError(
                "Maximum players cannot be lower than minimum players."
            )

        if self.mode == GameMode.SINGLE_PLAYER:
            if self.min_players != 1 or self.max_players != 1:
                raise RegistryError(
                    "Single-player games must have exactly one player."
                )

        if self.mode == GameMode.MULTIPLAYER:
            if self.min_players < 2:
                raise RegistryError(
                    "Multiplayer games must require at least two players."
                )

        object.__setattr__(self, "tags", tuple(
            tag.strip().lower()
            for tag in self.tags
            if isinstance(tag, str) and tag.strip()
        ))


# =========================================================
# GAME REGISTRY
# =========================================================

class GameRegistry:
    """
    Stores and manages all registered game definitions.

    Responsibilities:
    - Register games
    - Prevent duplicate game IDs
    - Retrieve game definitions
    - Filter games by mode
    - Unregister games

    This module is independent of Discord and the database.
    """

    def __init__(self) -> None:
        self._games: dict[str, GameDefinition] = {}

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    def register(self, definition: GameDefinition) -> GameDefinition:
        if not isinstance(definition, GameDefinition):
            raise RegistryError(
                "Only GameDefinition instances can be registered."
            )

        game_id = definition.game_id

        if game_id in self._games:
            raise RegistryError(
                f"Game '{game_id}' is already registered."
            )

        self._games[game_id] = definition
        return definition

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    def get(self, game_id: str) -> GameDefinition | None:
        if not isinstance(game_id, str):
            return None

        return self._games.get(game_id.strip().lower())

    def require(self, game_id: str) -> GameDefinition:
        definition = self.get(game_id)

        if definition is None:
            raise RegistryError(
                f"Game '{game_id}' is not registered."
            )

        return definition

    # -----------------------------------------------------
    # LIST
    # -----------------------------------------------------

    def all(self) -> tuple[GameDefinition, ...]:
        return tuple(self._games.values())

    def by_mode(self, mode: GameMode) -> tuple[GameDefinition, ...]:
        if not isinstance(mode, GameMode):
            raise RegistryError("Invalid game mode.")

        return tuple(
            game
            for game in self._games.values()
            if game.mode == mode
        )

    def single_player_games(self) -> tuple[GameDefinition, ...]:
        return self.by_mode(GameMode.SINGLE_PLAYER)

    def multiplayer_games(self) -> tuple[GameDefinition, ...]:
        return self.by_mode(GameMode.MULTIPLAYER)

    # -----------------------------------------------------
    # CHECK
    # -----------------------------------------------------

    def contains(self, game_id: str) -> bool:
        return self.get(game_id) is not None

    @property
    def count(self) -> int:
        return len(self._games)

    @property
    def game_ids(self) -> tuple[str, ...]:
        return tuple(self._games.keys())

    # -----------------------------------------------------
    # REMOVE
    # -----------------------------------------------------

    def unregister(self, game_id: str) -> GameDefinition:
        normalized_id = game_id.strip().lower()

        if normalized_id not in self._games:
            raise RegistryError(
                f"Game '{normalized_id}' is not registered."
            )

        return self._games.pop(normalized_id)

    def clear(self) -> None:
        self._games.clear()
