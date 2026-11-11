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
- Session lifecycle notifications
- Match results and cancellation
- Optional SQLite persistence
"""

from __future__ import annotations

import asyncio
import inspect
import secrets
from enum import Enum

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .repository import SQLiteSessionRepository


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
    Central manager for all game sessions.

    Session listeners receive:
        callback(session, user_id, event)

    Supported events:
        disconnected
        reconnected
        surrendered
        disconnect_expired

    Callbacks may be synchronous or asynchronous.

    Persistence:
        - SQLite storage is optional.
        - Only lobby sessions are restored after restart.
        - Running matches are not resumed automatically.
    """

    VALID_RESULTS = {"win", "loss", "draw"}

    def __init__(
        self,
        disconnect_grace_seconds: int = 30,
        repository: SQLiteSessionRepository | None = None,
    ):
        if disconnect_grace_seconds < 0:
            raise ValueError("Disconnect grace period cannot be negative.")

        self.disconnect_grace_seconds = disconnect_grace_seconds
        self.repository = repository

        self._sessions: dict[str, GameSession] = {}

        self._user_sessions: dict[tuple[str, str], str] = {}

        self._disconnect_tasks: dict[
            tuple[str, str],
            asyncio.Task,
        ] = {}

        self._session_listeners: dict[
            str,
            set[Callable[[GameSession, str, str], Any]],
        ] = {}
        
        self._completion_listeners: set[
            Callable[[GameSession], Any]
        ] = set()
        self._lock = asyncio.Lock()

    # =====================================================
    # SERIALIZATION
    # =====================================================

    @staticmethod
    def _datetime_to_string(
        value: datetime | None,
    ) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _string_to_datetime(
        value: str | None,
    ) -> datetime | None:
        if value is None:
            return None

        return datetime.fromisoformat(value)

    @classmethod
    def _serialize_session(
        cls,
        session: GameSession,
    ) -> dict[str, Any]:

        return {
            "session_id": session.session_id,
            "guild_id": session.guild_id,
            "game_id": session.game_id,
            "host_id": session.host_id,
            "min_players": session.min_players,
            "max_players": session.max_players,
            "status": session.status.value,
            "metadata": dict(session.metadata),
            "created_at": cls._datetime_to_string(
                session.created_at
            ),
            "started_at": cls._datetime_to_string(
                session.started_at
            ),
            "finished_at": cls._datetime_to_string(
                session.finished_at
            ),
            "players": {
                user_id: {
                    "user_id": player.user_id,
                    "username": player.username,
                    "status": player.status.value,
                    "joined_at": cls._datetime_to_string(
                        player.joined_at
                    ),
                    "disconnected_at": cls._datetime_to_string(
                        player.disconnected_at
                    ),
                    "result": player.result,
                }
                for user_id, player in session.players.items()
            },
        }

    @classmethod
    def _deserialize_session(
        cls,
        data: Mapping[str, Any],
    ) -> GameSession:

        players_data = data.get("players", {})

        if not isinstance(players_data, Mapping):
            raise ValueError("Invalid session players data.")

        players: dict[str, SessionPlayer] = {}

        for user_id, player_data in players_data.items():
            if not isinstance(player_data, Mapping):
                raise ValueError("Invalid player data.")

            normalized_user_id = str(user_id)

            players[normalized_user_id] = SessionPlayer(
                user_id=str(
                    player_data.get("user_id", normalized_user_id)
                ),
                username=str(player_data["username"]),
                status=PlayerStatus(
                    player_data.get(
                        "status",
                        PlayerStatus.ACTIVE.value,
                    )
                ),
                joined_at=(
                    cls._string_to_datetime(
                        player_data.get("joined_at")
                    )
                    or datetime.now(timezone.utc)
                ),
                disconnected_at=cls._string_to_datetime(
                    player_data.get("disconnected_at")
                ),
                result=player_data.get("result"),
            )

        return GameSession(
            session_id=str(data["session_id"]),
            guild_id=str(data["guild_id"]),
            game_id=str(data["game_id"]),
            host_id=str(data["host_id"]),
            min_players=int(data["min_players"]),
            max_players=int(data["max_players"]),
            status=SessionStatus(data["status"]),
            players=players,
            metadata=dict(data.get("metadata") or {}),
            created_at=(
                cls._string_to_datetime(data.get("created_at"))
                or datetime.now(timezone.utc)
            ),
            started_at=cls._string_to_datetime(
                data.get("started_at")
            ),
            finished_at=cls._string_to_datetime(
                data.get("finished_at")
            ),
        )

    async def _persist_session_unlocked(
        self,
        session: GameSession,
    ) -> None:
        """
        Persist a session while the manager lock is held.

        Keeping the write ordered with state changes prevents
        concurrent operations from saving stale snapshots.
        """

        if self.repository is None:
            return

        await self.repository.save_session(
            self._serialize_session(session)
        )

    async def _delete_persisted_session_unlocked(
        self,
        session_id: str,
    ) -> None:

        if self.repository is None:
            return

        await self.repository.delete_session(session_id)

    # =====================================================
    # INITIALIZATION AND RECOVERY
    # =====================================================

    async def initialize(self) -> None:
        """
        Initialize SQLite storage and restore recoverable lobbies.

        Running, completed and cancelled sessions are not restored.
        Running matches require game-specific state recovery, which
        is intentionally not implemented here.
        """

        if self.repository is None:
            return

        await self.repository.initialize()

        stored_sessions = await self.repository.load_sessions()

        async with self._lock:
            self._sessions.clear()
            self._user_sessions.clear()
            self._disconnect_tasks.clear()
            self._session_listeners.clear()

            for stored_data in stored_sessions:
                session_id = str(
                    stored_data.get("session_id", "")
                )

                try:
                    session = self._deserialize_session(
                        stored_data
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    if session_id:
                        await self._delete_persisted_session_unlocked(
                            session_id
                        )
                    continue

                if session.status != SessionStatus.LOBBY:
                    await self._delete_persisted_session_unlocked(
                        session.session_id
                    )
                    continue

                if not session.players:
                    await self._delete_persisted_session_unlocked(
                        session.session_id
                    )
                    continue

                if session.host_id not in session.players:
                    await self._delete_persisted_session_unlocked(
                        session.session_id
                    )
                    continue

                if len(session.players) > session.max_players:
                    await self._delete_persisted_session_unlocked(
                        session.session_id
                    )
                    continue

                conflicting_user = any(
                    (session.guild_id, user_id)
                    in self._user_sessions
                    for user_id in session.players
                )

                if conflicting_user:
                    await self._delete_persisted_session_unlocked(
                        session.session_id
                    )
                    continue

                self._sessions[session.session_id] = session

                for user_id in session.players:
                    self._user_sessions[
                        (session.guild_id, user_id)
                    ] = session.session_id

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
    def _require_host(session: GameSession, user_id: str) -> None:
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

        self._session_listeners.pop(session.session_id, None)

    async def _notify_session_listeners(
        self,
        session_id: str,
        user_id: str,
        event: str,
    ) -> None:
        """
        Notify listeners outside the manager lock.

        Listener failures must not undo or block a session state change.
        """

        async with self._lock:
            session = self._sessions.get(session_id)
            listeners = tuple(
                self._session_listeners.get(session_id, set())
            )

        if session is None or not listeners:
            return

        for callback in listeners:
            try:
                result = callback(session, user_id, event)

                if inspect.isawaitable(result):
                    await result

            except Exception:
                continue

    # =====================================================
    # SESSION LISTENERS
    # =====================================================

    def add_session_listener(
        self,
        session_id: str,
        callback: Callable[[GameSession, str, str], Any],
    ) -> None:

        if not callable(callback):
            raise SessionError("Session listener must be callable.")

        session_id = str(session_id)

        if session_id not in self._sessions:
            raise SessionError("Session does not exist.")

        self._session_listeners.setdefault(
            session_id,
            set(),
        ).add(callback)

    def remove_session_listener(
        self,
        session_id: str,
        callback: Callable[[GameSession, str, str], Any],
    ) -> None:

        session_id = str(session_id)

        listeners = self._session_listeners.get(session_id)

        if listeners is None:
            return

        listeners.discard(callback)

        if not listeners:
            self._session_listeners.pop(session_id, None)
   
    def add_completion_listener(
        self,
        callback: Callable[[GameSession], Any],
    ) -> None:

        if not callable(callback):
            raise SessionError(
                "Completion listener must be callable."
            )

        self._completion_listeners.add(callback)
        
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

            await self._persist_session_unlocked(session)

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

            await self._persist_session_unlocked(session)

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
        notify_surrender = False

        async with self._lock:
            session = self._get_session_unlocked(session_id)

            player = session.players.get(user_id)

            if player is None:
                raise SessionError("You are not in this session.")

            if session.status == SessionStatus.LOBBY:
                session.players.pop(user_id, None)

                self._user_sessions.pop(
                    (session.guild_id, user_id),
                    None,
                )

                if user_id == session.host_id:
                    if session.players:
                        session.host_id = next(iter(session.players))
                    else:
                        session.status = SessionStatus.CANCELLED
                        self._sessions.pop(session.session_id, None)
                        self._session_listeners.pop(
                            session.session_id,
                            None,
                        )

                        await self._delete_persisted_session_unlocked(
                            session.session_id
                        )

                        return session

                await self._persist_session_unlocked(session)

                return session

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

                    notify_surrender = True

                await self._persist_session_unlocked(session)

                result_session = session


            else:
                raise SessionError("This session is no longer active.")

        if notify_surrender:
            await self._notify_session_listeners(
                session.session_id,
                user_id,
                "surrendered",
            )

        return result_session

    # =====================================================
    # LOBBY CAPACITY
    # =====================================================

    async def set_lobby_capacity(
        self,
        session_id: str,
        host_id: str | int,
        max_players: int,
    ) -> GameSession:
        """Allow the lobby host to change the player limit."""

        host_id = self._normalize_id(host_id)

        if (
            not isinstance(max_players, int)
            or isinstance(max_players, bool)
        ):
            raise SessionError("Player limit must be an integer.")

        if not 1 <= max_players <= 30:
            raise SessionError(
                "Player limit must be between 1 and 30."
            )

        async with self._lock:
            session = self._get_session_unlocked(session_id)

            self._require_host(session, host_id)

            if session.status != SessionStatus.LOBBY:
                raise SessionError(
                    "Player limit can only be changed in the lobby."
                )

            if max_players < session.min_players:
                raise SessionError(
                    f"At least {session.min_players} players are required."
                )

            if max_players < session.player_count:
                raise SessionError(
                    "Player limit cannot be lower than current players."
                )

            session.max_players = max_players

            await self._persist_session_unlocked(session)

            return session

    # =====================================================
    # KICK PLAYER
    # =====================================================

    async def kick_player(
        self,
        session_id: str,
        host_id: str | int,
        target_id: str | int,
    ) -> GameSession:
        """Allow the lobby host to remove a player."""

        host_id = self._normalize_id(host_id)
        target_id = self._normalize_id(target_id)

        async with self._lock:
            session = self._get_session_unlocked(session_id)

            self._require_host(session, host_id)

            if session.status != SessionStatus.LOBBY:
                raise SessionError(
                    "Players can only be kicked while the lobby is open."
                )

            if target_id == session.host_id:
                raise SessionError(
                    "The lobby host cannot kick themselves."
                )

            if target_id not in session.players:
                raise SessionError(
                    "That player is not in this lobby."
                )

            session.players.pop(target_id, None)

            self._user_sessions.pop(
                (session.guild_id, target_id),
                None,
            )

            await self._persist_session_unlocked(session)

            return session

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

            await self._persist_session_unlocked(session)

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

            disconnect_time = player.disconnected_at
            key = (session.session_id, user_id)

            self._cancel_disconnect_task_unlocked(
                session.session_id,
                user_id,
            )

            await self._persist_session_unlocked(session)

            task = asyncio.create_task(
                self._expire_disconnect(
                    session.session_id,
                    user_id,
                    disconnect_time,
                )
            )

            self._disconnect_tasks[key] = task

        await self._notify_session_listeners(
            session.session_id,
            user_id,
            "disconnected",
        )

        return session

    async def reconnect(
        self,
        session_id: str,
        user_id: str | int,
    ) -> bool:

        user_id = self._normalize_id(user_id)
        event: str | None = None

        async with self._lock:
            session = self._get_session_unlocked(session_id)

            if session.status != SessionStatus.RUNNING:
                return False

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

                event = "disconnect_expired"
                reconnected = False

            else:
                self._cancel_disconnect_task_unlocked(
                    session.session_id,
                    user_id,
                )

                player.status = PlayerStatus.ACTIVE
                player.disconnected_at = None

                event = "reconnected"
                reconnected = True

            await self._persist_session_unlocked(session)

        if event is not None:
            await self._notify_session_listeners(
                session.session_id,
                user_id,
                event,
            )

        return reconnected

    async def _expire_disconnect(
        self,
        session_id: str,
        user_id: str,
        disconnect_time: datetime,
    ) -> None:

        key = (session_id, user_id)
        current_task = asyncio.current_task()
        expired = False

        try:
            await asyncio.sleep(self.disconnect_grace_seconds)

            async with self._lock:
                session = self._sessions.get(session_id)

                if session is None:
                    return

                if session.status != SessionStatus.RUNNING:
                    return

                player = session.players.get(user_id)

                if player is None:
                    return

                if player.disconnected_at != disconnect_time:
                    return

                if player.status == PlayerStatus.DISCONNECTED:
                    player.status = PlayerStatus.SURRENDERED
                    player.disconnected_at = None
                    expired = True

                    await self._persist_session_unlocked(session)

            if expired:
                await self._notify_session_listeners(
                    session_id,
                    user_id,
                    "disconnect_expired",
                )

        except asyncio.CancelledError:
            pass

        finally:
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

            await self._persist_session_unlocked(session)

        for callback in tuple(self._completion_listeners):
            try:
                result = callback(session)

                if inspect.isawaitable(result):
                    await result

            except Exception:
                continue

        return session
        
    # =====================================================
    # CANCEL RUNNING SESSION
    # =====================================================

    async def cancel_running(
        self,
        session_id: str,
        reason: str | None = None,
    ) -> GameSession:

        async with self._lock:
            session = self._get_session_unlocked(session_id)

            if session.status != SessionStatus.RUNNING:
                raise SessionError(
                    "Only a running match can be cancelled this way."
                )

            session.status = SessionStatus.CANCELLED
            session.finished_at = datetime.now(timezone.utc)

            if reason:
                session.metadata["cancellation_reason"] = str(reason)

            self._remove_session_indexes_unlocked(session)

            await self._persist_session_unlocked(session)

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
            session.finished_at = datetime.now(timezone.utc)

            self._remove_session_indexes_unlocked(session)
            self._sessions.pop(session.session_id, None)

            await self._delete_persisted_session_unlocked(
                session.session_id
            )

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
        """Cancel background disconnect timers."""

        async with self._lock:
            tasks = list(self._disconnect_tasks.values())

            self._disconnect_tasks.clear()
            self._session_listeners.clear()

            for task in tasks:
                if not task.done():
                    task.cancel()

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )
