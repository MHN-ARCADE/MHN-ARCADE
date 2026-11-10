
"""
MHN ARCADE V3 - Runtime

Central runtime for the V3 game engine.
Connects:
- Game sessions
- XP progression
- Player ranks
- Achievements
- Result recovery

V2 remains completely independent.
"""

from __future__ import annotations

import logging
import os

from pathlib import Path
from typing import Any, Callable

from .achievements import V3AchievementManager
from .catalog import build_default_registry
from .core import SessionManager
from .lobby import LobbyManager
from .progression import V3ProgressionManager
from .registry import GameRegistry
from .repository import SQLiteSessionRepository
from .runner import GameRunner


logger = logging.getLogger("mhn.arcade.v3.runtime")


class RuntimeError(Exception):
    """Raised when the V3 runtime cannot be initialized."""


class V3Runtime:
    """Central runtime for MHN ARCADE V3."""

    def __init__(
        self,
        db_path: str | Path | None = None,
    ) -> None:

        selected_db_path = (
            db_path
            or os.getenv("MHN_ARCADE_V3_DB_PATH")
            or "data/mhn_arcade_v3.db"
        )

        self.repository = SQLiteSessionRepository(
            db_path=selected_db_path
        )

        # All V3 systems share the same isolated database.
        self.achievements = V3AchievementManager(
            db_path=self.repository.db_path
        )

        self.progression = V3ProgressionManager(
            db_path=self.repository.db_path
        )

        self.achievement_announcement_callback: (
            Callable[[list[dict[str, str]]], Any] | None
        ) = None

        self.sessions = SessionManager(
            repository=self.repository
        )

        self.sessions.add_completion_listener(
            self._on_session_completed
        )

        self.lobbies = LobbyManager(
            session_manager=self.sessions
        )

        self.registry: GameRegistry = build_default_registry()

        self.runner = GameRunner(
            registry=self.registry,
            lobby_manager=self.lobbies,
        )

        self._initialized = False
        self._closed = False

    @property
    def initialized(self) -> bool:
        return self._initialized and not self._closed

    # =====================================================
    # COMPLETED GAME PROCESSING
    # =====================================================

    async def _on_session_completed(
        self,
        session: Any,
    ) -> None:
        """
        Process completed games through both V3 systems.

        XP and achievements use independent idempotency
        checks, so retrying a completed session does not
        award duplicate progress.
        """

        session_id = getattr(
            session,
            "session_id",
            "unknown",
        )

        # Process XP independently.
        try:
            rewards = await self.progression.record_completed_game(
                session
            )

            if rewards:
                logger.info(
                    "V3 XP processed for session %s: %s player(s)",
                    session_id,
                    len(rewards),
                )

        except Exception:
            logger.exception(
                "V3 XP processing failed for session %s",
                session_id,
            )

        # Process achievements independently.
        try:
            unlocked = await self.achievements.record_completed_game(
                session
            )

            if not unlocked:
                return

            callback = self.achievement_announcement_callback

            if callable(callback):
                result = callback(unlocked)

                if hasattr(result, "__await__"):
                    await result

        except Exception:
            logger.exception(
                "V3 achievement processing failed for session %s",
                session_id,
            )

    # =====================================================
    # INITIALIZATION AND RECOVERY
    # =====================================================

    async def initialize(self) -> "V3Runtime":
        """Initialize V3 storage and recover completed results."""

        if self._closed:
            raise RuntimeError(
                "A closed V3 runtime cannot be initialized again."
            )

        if self._initialized:
            return self

        try:
            # Initialize the shared database tables first.
            await self.repository.initialize()

            await self.achievements.initialize()
            await self.progression.initialize()

            # Recover completed sessions in case the process
            # stopped before XP or achievements were processed.
            stored_sessions = await self.repository.load_sessions()

            for stored_data in stored_sessions:

                if stored_data.get("status") != "completed":
                    continue

                try:
                    session = SessionManager._deserialize_session(
                        stored_data
                    )

                    # Each system has its own duplicate protection.
                    await self.progression.record_completed_game(
                        session
                    )

                    await self.achievements.record_completed_game(
                        session
                    )

                except Exception:
                    logger.exception(
                        "Could not recover V3 result for session %s",
                        stored_data.get("session_id", "unknown"),
                    )

            await self.sessions.initialize()

        except Exception as exc:
            raise RuntimeError(
                f"V3 runtime initialization failed: {exc}"
            ) from exc

        self._initialized = True

        logger.info(
            "MHN ARCADE V3 initialized successfully."
        )

        return self

    # =====================================================
    # STATUS
    # =====================================================

    def require_initialized(self) -> None:
        if not self.initialized:
            raise RuntimeError(
                "V3 runtime has not been initialized."
            )

    def get_status(self) -> dict[str, Any]:
        return {
            "initialized": self.initialized,
            "closed": self._closed,
            "registered_games": self.registry.count,
            "game_ids": list(self.registry.game_ids),
            "database": str(self.repository.db_path),
            "achievements_enabled": self.initialized,
            "progression_enabled": self.initialized,
        }

    # =====================================================
    # SHUTDOWN
    # =====================================================

    async def shutdown(self) -> None:
        if self._closed:
            return

        await self.sessions.shutdown()

        self._initialized = False
        self._closed = True


# =========================================================
# RUNTIME FACTORY
# =========================================================

async def create_v3_runtime(
    db_path: str | Path | None = None,
) -> V3Runtime:
    """Create and initialize a ready-to-use V3 runtime."""

    runtime = V3Runtime(db_path=db_path)

    try:
        await runtime.initialize()

    except Exception:
        await runtime.shutdown()
        raise

    return runtime
