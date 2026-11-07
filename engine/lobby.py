"""
MHN ARCADE V3 - Lobby Manager

A simple lobby interface built on top of SessionManager.

This module handles lobby operations.
Discord buttons and commands will be connected later.
"""

from __future__ import annotations

from typing import Any, Mapping

from .core import GameSession, SessionManager


class LobbyManager:
    """
    Lobby operations for multiplayer games.

    This class does not depend on Discord.py.
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
        max_players: int = 12,
        metadata: Mapping[str, Any] | None = None,
    ) -> GameSession:

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
    # START GAME
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
