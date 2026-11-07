"""
MHN ARCADE V3 - Game Runner

Connects the game registry with the lobby and session engine.

Responsibilities:
- Validate game definitions
- Create multiplayer lobbies
- Start registered multiplayer games
- Prepare single-player games
- Create game handlers when available

This module is independent from Discord.py and database code.
"""

from __future__ import annotations

import inspect

from dataclasses import dataclass
from typing import Any, Mapping

from .core import GameSession, SessionStatus
from .lobby import LobbyManager
from .registry import GameDefinition, GameMode, GameRegistry


# =========================================================
# ERRORS
# =========================================================

class RunnerError(Exception):
    """Raised when a game cannot be prepared or launched."""


# =========================================================
# GAME LAUNCH RESULT
# =========================================================

@dataclass
class GameLaunch:
    """
    Represents a prepared or started game.

    session:
        Multiplayer session, or None for single-player games.

    definition:
        Registered game definition.

    handler:
        Game-specific handler instance, if one is available.
    """

    definition: GameDefinition
    session: GameSession | None = None
    handler: Any = None


# =========================================================
# GAME RUNNER
# =========================================================

class GameRunner:
    """
    Coordinates game definitions, lobbies, sessions, and handlers.

    Game mechanics should remain inside their own handler modules.
    """

    def __init__(
        self,
        registry: GameRegistry,
        lobby_manager: LobbyManager | None = None,
    ) -> None:

        if not isinstance(registry, GameRegistry):
            raise RunnerError(
                "GameRunner requires a valid GameRegistry."
            )

        self.registry = registry
        self.lobbies = lobby_manager or LobbyManager()

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _get_definition(
        self,
        game_id: str,
    ) -> GameDefinition:

        if not isinstance(game_id, str) or not game_id.strip():
            raise RunnerError("Game ID cannot be empty.")

        definition = self.registry.get(game_id)

        if definition is None:
            raise RunnerError(
                f"Game '{game_id}' is not registered."
            )

        return definition

    @staticmethod
    def _validate_player_count(
        definition: GameDefinition,
        player_count: int,
    ) -> None:

        if (
            not isinstance(player_count, int)
            or isinstance(player_count, bool)
        ):
            raise RunnerError("Player count must be an integer.")

        if player_count < definition.min_players:
            raise RunnerError(
                f"{definition.name_en} requires at least "
                f"{definition.min_players} players."
            )

        if player_count > definition.max_players:
            raise RunnerError(
                f"{definition.name_en} supports at most "
                f"{definition.max_players} players."
            )

    @staticmethod
    async def _create_handler(
        definition: GameDefinition,
        **context: Any,
    ) -> Any:

        factory = definition.handler_factory

        if factory is None:
            return None

        try:
            handler = factory(**context)

            if inspect.isawaitable(handler):
                handler = await handler

            return handler

        except Exception as exc:
            raise RunnerError(
                f"Could not create handler for "
                f"'{definition.game_id}': {exc}"
            ) from exc

    # =====================================================
    # CREATE MULTIPLAYER LOBBY
    # =====================================================

    async def create_multiplayer_lobby(
        self,
        game_id: str,
        guild_id: str | int,
        host_id: str | int,
        host_name: str,
        min_players: int | None = None,
        max_players: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> GameSession:

        definition = self._get_definition(game_id)

        if definition.mode != GameMode.MULTIPLAYER:
            raise RunnerError(
                f"'{definition.game_id}' is not a multiplayer game."
            )

        selected_min = (
            definition.min_players
            if min_players is None
            else min_players
        )

        selected_max = (
            definition.max_players
            if max_players is None
            else max_players
        )

        if (
            not isinstance(selected_min, int)
            or isinstance(selected_min, bool)
            or not isinstance(selected_max, int)
            or isinstance(selected_max, bool)
        ):
            raise RunnerError(
                "Lobby player limits must be integers."
            )

        if selected_min < definition.min_players:
            raise RunnerError(
                "Lobby minimum cannot be lower than "
                "the game's registered minimum."
            )

        if selected_max > definition.max_players:
            raise RunnerError(
                "Lobby maximum cannot exceed "
                "the game's registered maximum."
            )

        if selected_max < selected_min:
            raise RunnerError(
                "Lobby maximum cannot be lower than minimum."
            )

        if selected_min < 2:
            raise RunnerError(
                "A multiplayer lobby must require at least "
                "two players."
            )

        lobby_metadata = dict(metadata or {})

        # Keep the registered game ID in session metadata.
        lobby_metadata["game_name_en"] = definition.name_en
        lobby_metadata["game_name_ar"] = definition.name_ar
        lobby_metadata["game_mode"] = definition.mode.value

        return await self.lobbies.create(
            guild_id=guild_id,
            game_id=definition.game_id,
            host_id=host_id,
            host_name=host_name,
            min_players=selected_min,
            max_players=selected_max,
            metadata=lobby_metadata,
        )

    # =====================================================
    # START MULTIPLAYER GAME
    # =====================================================

    async def start_multiplayer_game(
        self,
        session_id: str,
        host_id: str | int,
    ) -> GameLaunch:

        session = await self.lobbies.get(session_id)

        if session is None:
            raise RunnerError("Multiplayer session does not exist.")

        definition = self._get_definition(session.game_id)

        if definition.mode != GameMode.MULTIPLAYER:
            raise RunnerError(
                "This session is not a multiplayer game."
            )

        if session.status != SessionStatus.LOBBY:
            raise RunnerError(
                "This session is not waiting in a lobby."
            )

        self._validate_player_count(
            definition,
            session.player_count,
        )

        # Create the handler before starting the session.
        # If handler creation fails, the lobby remains open.
        handler = await self._create_handler(
            definition,
            session=session,
            definition=definition,
        )

        started_session = await self.lobbies.start(
            session_id=session_id,
            host_id=host_id,
        )

        return GameLaunch(
            definition=definition,
            session=started_session,
            handler=handler,
        )

    # =====================================================
    # PREPARE SINGLE-PLAYER GAME
    # =====================================================

    async def prepare_single_player_game(
        self,
        game_id: str,
        player_id: str | int,
        player_name: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> GameLaunch:

        definition = self._get_definition(game_id)

        if definition.mode != GameMode.SINGLE_PLAYER:
            raise RunnerError(
                f"'{definition.game_id}' is not a single-player game."
            )

        context = {
            "player_id": str(player_id),
            "player_name": str(player_name),
            "metadata": dict(metadata or {}),
            "definition": definition,
        }

        handler = await self._create_handler(
            definition,
            **context,
        )

        return GameLaunch(
            definition=definition,
            session=None,
            handler=handler,
        )

    # =====================================================
    # GAME LOOKUP
    # =====================================================

    def get_game(
        self,
        game_id: str,
    ) -> GameDefinition:

        return self._get_definition(game_id)

    def list_games(
        self,
        mode: GameMode | None = None,
    ) -> tuple[GameDefinition, ...]:

        if mode is None:
            return self.registry.all()

        return self.registry.by_mode(mode)

    # =====================================================
    # CHECK GAME AVAILABILITY
    # =====================================================

    def can_launch(
        self,
        game_id: str,
        player_count: int,
    ) -> bool:

        definition = self._get_definition(game_id)

        try:
            self._validate_player_count(
                definition,
                player_count,
            )

        except RunnerError:
            return False

        return True
