"""
MHN ARCADE V3 - Core Engine

Discord-independent session engine.
Handles:
- Game sessions
- Player registration
- Lobby state
- Host permissions
- Voluntary leaving
- Disconnect and reconnect grace period
- Match results

This module does not contain Discord UI or database code.
"""

from __future__ import annotations

import asyncio
import secrets

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


# =========================================================
# ENUMS
# =========================================================

class SessionStatus(str, Enum):
    LOBBY = "lobby"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlayerStatus(str, Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    SURRENDERED = "surrendered"
    ELIMINATED = "eliminated"
    WINNER = "winner"
    DRAW = "draw"


# =========================================================
# ERRORS
# =========================================================

class SessionError(Exception):
    """Raised when a session operation cannot be completed."""


# =========================================================
# DATA MODELS
# =========================================================

@dataclass
class SessionPlayer:
    user_id: str
    username: str

    status: PlayerStatus = PlayerStatus.ACTIVE
    joined_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    disconnected_at: datetime | None = None
    result: str | None = None


@dataclass
class GameSession:
    session_id: str
    guild_id: str
    game_id: str

    host_id: str

    min_players: int
    max_players: int

    status: SessionStatus = SessionStatus.LOBBY

    players: dict[str, SessionPlayer] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def active_players(self) -> list[SessionPlayer]:
        return [
            player
            for player in self.players.values()
            if player.status == PlayerStatus.ACTIVE
        ]

    @property
    def remaining_players(self) -> list[SessionPlayer]:
        return [
            player
            for player in self.players.values()
            if player.status in (
                PlayerStatus.ACTIVE,
                PlayerStatus.DISCONNECTED,
            )
        ]

    @property
    def is_full(self) -> bool:
        return self.player_count >= self.max_players

    def get_player(self, user_id: str | int) -> SessionPlayer | None:
        return self.players.get(str(user_id))


# =========================================================
# SESSION MANAGER
# =========================================================

class SessionManager:
    """
    Central manager for all active game sessions.

    The manager is independent from Discord.py.
    Discord commands, buttons and game logic should call
    this manager instead of modifying sessions directly.
    """

    VALID_RESULTS = {"win", "loss", "draw"}

    def __init__(self, disconnect_grace_seconds: int = 30):
        if disconnect_grace_seconds < 0:
            raise ValueError("Disconnect grace period cannot be negative.")

        self.disconnect_grace_seconds = disconnect_grace_seconds

        self._sessions: dict[str, GameSession] = {}

        # A player can only belong to one active session
        # per Discord server.
        self._user_sessions: dict[tuple[str, str], str] = {}

        self._disconnect_tasks: dict[
            tuple[str, str],
            asyncio.Task,
        ] = {}

        self._lock = asyncio.Lock()

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    @staticmethod
    def _normalize_id(value: str | int) -> str:
        return str(value)

    def _get_session_unlocked(self, session_id: str) -> GameSession:
        session = self._sessions.get(str(session_id))

        if session is None:
            raise SessionError("Session does not exist.")

        return session

    @staticmethod
    def _require_host(
        session: GameSession,
        user_id: str,
    ) -> None:
        if session.host_id != user_id:
            raise SessionError("Only the session host can do this.")

    def _cancel_disconnect_task_unlocked(
        self,
        session_id: str,
        user_id: str,
    ) -> None:
        key = (session_id, user_id)
        task = self._disconnect_tasks.pop(key, None)

        if task is not None and not task.done():
            task.cancel()

    def _remove_session_indexes_unlocked(
        self,
        session: GameSession,
    ) -> None:
        for user_id in list(session.players):
            key = (session.guild_id, user_id)

            if self._user_sessions.get(key) == session.session_id:
                self._user_sessions.pop(key, None)

            self._cancel_disconnect_task_unlocked(
                session.session_id,
                user_id,
            )

    # =====================================================
    # CREATE SESSION
    # =====================================================

    async def create_session(
        self,
        guild_id: str | int,
        game_id: str,
        host_id: str | int,
        host_name: str,
        min_players: int = 3,
        max_players: int = 12,
        metadata: Mapping[str, Any] | None = None,
    ) -> GameSession:

        guild_id = self._normalize_id(guild_id)
        host_id = self._normalize_id(host_id)

        if not game_id or not game_id.strip():
            raise SessionError("Game ID cannot be empty.")

        if min_players < 1:
            raise SessionError("Minimum players must be at least 1.")

        if max_players < min_players:
            raise SessionError(
                "Maximum players cannot be lower than minimum players."
            )

        async with self._lock:

            user_key = (guild_id, host_id)

            if user_key in self._user_sessions:
                raise SessionError(
                    "This player is already in an active session."
                )

            session_id = secrets.token_urlsafe(6)

            while session_id in self._sessions:
                session_id = secrets.token_urlsafe(6)

            session = GameSession(
                session_id=session_id,
                guild_id=guild_id,
                game_id=game_id.strip(),
                host_id=host_id,
                min_players=min_players,
                max_players=max_players,
                metadata=dict(metadata or {}),
            )

            session.players[host_id] = SessionPlayer(
                user_id=host_id,
                username=str(host_name),
            )

            self._sessions[session_id] = session
            self._user_sessions[user_key] = session_id

            return session

    # =====================================================
    # JOIN SESSION
    # =====================================================

    async def join(
        self,
        session_id: str,
        user_id: str | int,
        username: str,
    ) -> GameSession:

        user_id = self._normalize_id(user_id)

        async with self._lock:

            session = self._get_session_unlocked(session_id)

            if session.status != SessionStatus.LOBBY:
                raise SessionError("This game has already started.")

            if user_id in session.players:
                raise SessionError("You are already in this lobby.")

            if session.is_full:
                raise SessionError("This lobby is full.")

            user_key = (session.guild_id, user_id)

            if user_key in self._user_sessions:
                raise SessionError(
                    "You are already participating in another session."
                )

            session.players[user_id] = SessionPlayer(
                user_id=user_id,
                username=str(username),
            )

            self._user_sessions[user_key] = session.session_id

            return session

    # =====================================================
    # LEAVE SESSION
    # =====================================================

    async def leave(
        self,
        session_id: str,
        user_id: str | int,
    ) -> GameSession:

        user_id = self._normalize_id(user_id)

        async with self._lock:

            session = self._get_session_unlocked(session_id)

            player = session.players.get(user_id)

            if player is None:
                raise SessionError("You are not in this session.")

            # Leaving before the game starts.
            if session.status == SessionStatus.LOBBY:

                session.players.pop(user_id, None)

                self._user_sessions.pop(
                    (session.guild_id, user_id),
                    None,
                )

                if user_id == session.host_id:

                    if session.players:
                        # Dictionary order preserves join order.
                        session.host_id = next(iter(session.players))
                    else:
                        session.status = SessionStatus.CANCELLED
                        self._sessions.pop(session.session_id, None)

                return session

            # Leaving after the game starts means surrender.
            if session.status == SessionStatus.RUNNING:

                if player.status in (
                    PlayerStatus.ACTIVE,
                    PlayerStatus.DISCONNECTED,
                ):
                    player.status = PlayerStatus.SURRENDERED
                    player.disconnected_at = None

                    self._cancel_disconnect_task_unlocked(
                        session.session_id,
                        user_id,
                    )

                return session

            raise SessionError("This session is no longer active.")

    # =====================================================
    # START SESSION
    # =====================================================

    async def start(
        self,
        session_id: str,
        user_id: str | int,
    ) -> GameSession:

        user_id = self._normalize_id(user_id)

        async with self._lock:

            session = self._get_session_unlocked(session_id)

            self._require_host(session, user_id)

            if session.status != SessionStatus.LOBBY:
                raise SessionError("This session cannot be started.")

            if session.player_count < session.min_players:
                raise SessionError(
                    f"At least {session.min_players} players are required."
                )

            session.status = SessionStatus.RUNNING
            session.started_at = datetime.now(timezone.utc)

            return session

    # =====================================================
    # DISCONNECT HANDLING
    # =====================================================

    async def mark_disconnected(
        self,
        session_id: str,
        user_id: str | int,
    ) -> GameSession:

        user_id = self._normalize_id(user_id)

        async with self._lock:

            session = self._get_session_unlocked(session_id)

            if session.status != SessionStatus.RUNNING:
                raise SessionError(
                    "Disconnect tracking is only available during a match."
                )

            player = session.players.get(user_id)

            if player is None:
                raise SessionError("Player does not exist in this session.")

            if player.status != PlayerStatus.ACTIVE:
                raise SessionError("Player is not currently active.")

            player.status = PlayerStatus.DISCONNECTED
            player.disconnected_at = datetime.now(timezone.utc)

            key = (session.session_id, user_id)

            self._cancel_disconnect_task_unlocked(
                session.session_id,
                user_id,
            )

            task = asyncio.create_task(
                self._expire_disconnect(
                    session.session_id,
                    user_id,
                    player.disconnected_at,
                )
            )

            self._disconnect_tasks[key] = task

            return session

    async def reconnect(
        self,
        session_id: str,
        user_id: str | int,
    ) -> bool:

        user_id = self._normalize_id(user_id)

        async with self._lock:

            session = self._get_session_unlocked(session_id)

            player = session.players.get(user_id)

            if player is None:
                raise SessionError("Player does not exist in this session.")

            if player.status == PlayerStatus.ACTIVE:
                return True

            if player.status != PlayerStatus.DISCONNECTED:
                return False

            if player.disconnected_at is None:
                return False

            elapsed = (
                datetime.now(timezone.utc) - player.disconnected_at
            ).total_seconds()

            if elapsed >= self.disconnect_grace_seconds:

                player.status = PlayerStatus.SURRENDERED
                player.disconnected_at = None

                self._cancel_disconnect_task_unlocked(
                    session.session_id,
                    user_id,
                )

                return False

            self._cancel_disconnect_task_unlocked(
                session.session_id,
                user_id,
            )

            player.status = PlayerStatus.ACTIVE
            player.disconnected_at = None

            return True

    async def _expire_disconnect(
        self,
        session_id: str,
        user_id: str,
        disconnect_time: datetime,
    ) -> None:

        key = (session_id, user_id)
        current_task = asyncio.current_task()

        try:
            await asyncio.sleep(self.disconnect_grace_seconds)

            async with self._lock:

                session = self._sessions.get(session_id)

                if session is None:
                    return

                player = session.players.get(user_id)

                if player is None:
                    return

                # Do not expire a newer disconnect period.
                if player.disconnected_at != disconnect_time:
                    return

                if player.status == PlayerStatus.DISCONNECTED:
                    player.status = PlayerStatus.SURRENDERED
                    player.disconnected_at = None

        except asyncio.CancelledError:
            pass

        finally:
            # Only remove the task entry if it still belongs
            # to this exact task.
            if self._disconnect_tasks.get(key) is current_task:
                self._disconnect_tasks.pop(key, None)

    # =====================================================
    # FINISH SESSION
    # =====================================================

    async def finish(
        self,
        session_id: str,
        results: Mapping[str | int, str],
        winner_id: str | int | None = None,
    ) -> GameSession:

        normalized_results = {
            self._normalize_id(user_id): str(result).lower()
            for user_id, result in results.items()
        }

        if not normalized_results:
            raise SessionError("Results cannot be empty.")

        if any(
            result not in self.VALID_RESULTS
            for result in normalized_results.values()
        ):
            raise SessionError(
                "Every result must be win, loss or draw."
            )

        if winner_id is not None:
            winner_id = self._normalize_id(winner_id)

        async with self._lock:

            session = self._get_session_unlocked(session_id)

            if session.status != SessionStatus.RUNNING:
                raise SessionError("This match is not running.")

            expected_players = set(session.players)
            submitted_players = set(normalized_results)

            if expected_players != submitted_players:
                raise SessionError(
                    "Results must include every player in the session."
                )

            if winner_id is not None:

                if winner_id not in session.players:
                    raise SessionError("Winner is not in this session.")

                if normalized_results[winner_id] != "win":
                    raise SessionError(
                        "The winner must have a win result."
                    )

            for user_id, result in normalized_results.items():

                player = session.players[user_id]
                player.result = result

                if result == "win":
                    player.status = PlayerStatus.WINNER

                elif result == "draw":
                    player.status = PlayerStatus.DRAW

                elif player.status != PlayerStatus.SURRENDERED:
                    player.status = PlayerStatus.ELIMINATED

                player.disconnected_at = None

            session.status = SessionStatus.COMPLETED
            session.finished_at = datetime.now(timezone.utc)

            self._remove_session_indexes_unlocked(session)

            return session

    # =====================================================
    # CANCEL LOBBY
    # =====================================================

    async def cancel_lobby(
        self,
        session_id: str,
        user_id: str | int,
    ) -> GameSession:

        user_id = self._normalize_id(user_id)

        async with self._lock:

            session = self._get_session_unlocked(session_id)

            self._require_host(session, user_id)

            if session.status != SessionStatus.LOBBY:
                raise SessionError(
                    "Only a lobby can be cancelled this way."
                )

            session.status = SessionStatus.CANCELLED

            self._remove_session_indexes_unlocked(session)

            self._sessions.pop(session.session_id, None)

            return session

    # =====================================================
    # GETTERS
    # =====================================================

    async def get_session(
        self,
        session_id: str,
    ) -> GameSession | None:

        async with self._lock:
            return self._sessions.get(str(session_id))

    async def get_user_session(
        self,
        guild_id: str | int,
        user_id: str | int,
    ) -> GameSession | None:

        guild_id = self._normalize_id(guild_id)
        user_id = self._normalize_id(user_id)

        async with self._lock:

            session_id = self._user_sessions.get(
                (guild_id, user_id)
            )

            if session_id is None:
                return None

            return self._sessions.get(session_id)

    async def list_sessions(
        self,
        guild_id: str | int | None = None,
        status: SessionStatus | None = None,
    ) -> list[GameSession]:

        async with self._lock:

            sessions = list(self._sessions.values())

            if guild_id is not None:
                guild_id = self._normalize_id(guild_id)

                sessions = [
                    session
                    for session in sessions
                    if session.guild_id == guild_id
                ]

            if status is not None:
                sessions = [
                    session
                    for session in sessions
                    if session.status == status
                ]

            return sessions

    # =====================================================
    # SHUTDOWN
    # =====================================================

    async def shutdown(self) -> None:
        """
        Cancel background disconnect timers.
        Call this when shutting down the bot.
        """

        async with self._lock:

            tasks = list(self._disconnect_tasks.values())

            self._disconnect_tasks.clear()

            for task in tasks:
                if not task.done():
                    task.cancel()

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )
