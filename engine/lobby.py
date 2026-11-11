
"""
MHN ARCADE V3 - Lobby Manager

Manages multiplayer lobby operations.
Discord buttons and commands are connected
through the V3 Discord interface.
"""

from __future__ import annotations

from typing import Any, Mapping

from .core import GameSession, SessionManager, SessionError


MAX_MULTIPLAYER_PLAYERS = 30


class LobbyManager:
    """
    Lobby operations for multiplayer games.

    The lobby creator is the host.
    Only the host can change capacity,
    kick players, start or close the lobby.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
    ):
        self.sessions = session_manager or SessionManager()

    # =====================================================
    # CREATE LOBBY
    # =====================================================

    async def create(
        self,
        guild_id: str | int,
        game_id: str,
        host_id: str | int,
        host_name: str,
        min_players: int = 3,
        max_players: int = MAX_MULTIPLAYER_PLAYERS,
        metadata: Mapping[str, Any] | None = None,
    ) -> GameSession:

        if not isinstance(max_players, int) or isinstance(max_players, bool):
            raise SessionError("Player limit must be an integer.")

        if not 1 <= max_players <= MAX_MULTIPLAYER_PLAYERS:
            raise SessionError(
                f"Player limit must be between 1 and "
                f"{MAX_MULTIPLAYER_PLAYERS}."
            )

        if min_players < 1 or min_players > max_players:
            raise SessionError("Invalid minimum player requirement.")

        return await self.sessions.create_session(
            guild_id=guild_id,
            game_id=game_id,
            host_id=host_id,
            host_name=host_name,
            min_players=min_players,
            max_players=max_players,
            metadata=metadata,
        )

    # =====================================================
    # JOIN LOBBY
    # =====================================================

    async def join(
        self,
        session_id: str,
        user_id: str | int,
        username: str,
    ) -> GameSession:

        return await self.sessions.join(
            session_id=session_id,
            user_id=user_id,
            username=username,
        )

    # =====================================================
    # LEAVE LOBBY / SURRENDER
    # =====================================================

    async def leave(
        self,
        session_id: str,
        user_id: str | int,
    ) -> GameSession:

        return await self.sessions.leave(
            session_id=session_id,
            user_id=user_id,
        )

    # =====================================================
    # CHANGE LOBBY CAPACITY
    # HOST ONLY
    # =====================================================

    async def set_capacity(
        self,
        session_id: str,
        host_id: str | int,
        max_players: int,
    ) -> GameSession:

        if (
            not isinstance(max_players, int)
            or isinstance(max_players, bool)
        ):
            raise SessionError("Player limit must be an integer.")

        if not 1 <= max_players <= MAX_MULTIPLAYER_PLAYERS:
            raise SessionError(
                f"Player limit must be between 1 and "
                f"{MAX_MULTIPLAYER_PLAYERS}."
            )

        return await self.sessions.set_lobby_capacity(
            session_id=session_id,
            host_id=host_id,
            max_players=max_players,
        )

    # =====================================================
    # KICK PLAYER
    # HOST ONLY
    # =====================================================

    async def kick(
        self,
        session_id: str,
        host_id: str | int,
        target_id: str | int,
    ) -> GameSession:

        return await self.sessions.kick_player(
            session_id=session_id,
            host_id=host_id,
            target_id=target_id,
        )

    # =====================================================
    # START GAME
    # HOST ONLY
    # =====================================================

    async def start(
        self,
        session_id: str,
        host_id: str | int,
    ) -> GameSession:

        return await self.sessions.start(
            session_id=session_id,
            user_id=host_id,
        )

    # =====================================================
    # CLOSE LOBBY
    # HOST ONLY
    # =====================================================

    async def close(
        self,
        session_id: str,
        host_id: str | int,
    ) -> GameSession:

        return await self.sessions.cancel_lobby(
            session_id=session_id,
            user_id=host_id,
        )

    # =====================================================
    # GET LOBBY
    # =====================================================

    async def get(
        self,
        session_id: str,
    ) -> GameSession | None:

        return await self.sessions.get_session(session_id)

    # =====================================================
    # FIND PLAYER LOBBY
    # =====================================================

    async def get_player_lobby(
        self,
        guild_id: str | int,
        user_id: str | int,
    ) -> GameSession | None:

        return await self.sessions.get_user_session(
            guild_id=guild_id,
            user_id=user_id,
        )

    # =====================================================
    # LIST LOBBIES
    # =====================================================

    async def list(
        self,
        guild_id: str | int | None = None,
    ) -> list[GameSession]:

        return await self.sessions.list_sessions(
            guild_id=guild_id,
        )
