
"""
MHN ARCADE V3 - Runtime

Central runtime for the V3 game engine.

Responsibilities:
- Create isolated V3 SQLite storage
- Initialize and recover lobby sessions
- Build the game registry
- Connect sessions, lobbies, and game runner
- Provide a clean shutdown lifecycle

This module does not modify or start the V2 engine.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any

from .catalog import build_default_registry
from .core import SessionManager
from .lobby import LobbyManager
from .registry import GameRegistry
from .repository import SQLiteSessionRepository
from .runner import GameRunner


class RuntimeError(Exception):
    """Raised when the V3 runtime cannot be initialized."""


class V3Runtime:
    """
    Central runtime for MHN ARCADE V3.

    Create one runtime instance for the application.
    Initialize it during application startup and shut it
    down when the application stops.
    """

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

        self.sessions = SessionManager(
            repository=self.repository
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
        """Return whether the runtime is ready."""
        return self._initialized and not self._closed

    async def initialize(self) -> "V3Runtime":
        """
        Initialize database storage and restore recoverable
        lobby sessions.

        Safe to call more than once on the same runtime instance.
        """

        if self._closed:
            raise RuntimeError(
                "A closed V3 runtime cannot be initialized again."
            )

        if self._initialized:
            return self

        try:
            await self.sessions.initialize()

        except Exception as exc:
            raise RuntimeError(
                f"V3 runtime initialization failed: {exc}"
            ) from exc

        self._initialized = True

        return self

    def require_initialized(self) -> None:
        """Ensure the runtime is ready before game operations."""

        if not self.initialized:
            raise RuntimeError(
                "V3 runtime has not been initialized."
            )

    def get_status(self) -> dict[str, Any]:
        """Return a basic runtime status snapshot."""

        return {
            "initialized": self.initialized,
            "closed": self._closed,
            "registered_games": self.registry.count,
            "game_ids": list(self.registry.game_ids),
            "database": str(self.repository.db_path),
        }

    async def shutdown(self) -> None:
        """Stop background session tasks and close the runtime."""

        if self._closed:
            return

        await self.sessions.shutdown()

        self._initialized = False
        self._closed = True


async def create_v3_runtime(
    db_path: str | Path | None = None,
) -> V3Runtime:
    """
    Create and initialize a ready-to-use V3 runtime.

    Example:
        runtime = await create_v3_runtime()
    """

    runtime = V3Runtime(db_path=db_path)

    try:
        await runtime.initialize()

    except Exception:
        await runtime.shutdown()
        raise

    return runtime
