
"""
MHN ARCADE V3 - Session Repository

Persistent SQLite storage for V3 game sessions.
Uses isolated v3_ tables and preserves the existing V2 database.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3

from pathlib import Path
from typing import Any, Mapping


class SQLiteSessionRepository:
    """Stores serialized V3 sessions in SQLite."""

    def __init__(
        self,
        db_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(
            db_path
            or os.getenv("MHN_ARCADE_DB_PATH", "mhn_arcade.db")
        )

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    def _initialize_sync(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS v3_sessions (
                    session_id TEXT PRIMARY KEY,
                    guild_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                v3_sessions_guild_status_idx
                ON v3_sessions(guild_id, status)
                """
            )

    async def initialize(self) -> None:
        """Create V3 storage tables if they do not exist."""
        await asyncio.to_thread(self._initialize_sync)

    def _save_sync(
        self,
        session_data: Mapping[str, Any],
    ) -> None:
        data = dict(session_data)

        session_id = str(data["session_id"])
        guild_id = str(data["guild_id"])
        status = str(data["status"])

        payload = json.dumps(
            data,
            ensure_ascii=False,
            allow_nan=False,
        )

        with self._connect() as db:
            db.execute(
                """
                INSERT INTO v3_sessions (
                    session_id,
                    guild_id,
                    status,
                    payload,
                    updated_at
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)

                ON CONFLICT(session_id)
                DO UPDATE SET
                    guild_id = excluded.guild_id,
                    status = excluded.status,
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    session_id,
                    guild_id,
                    status,
                    payload,
                ),
            )

    async def save_session(
        self,
        session_data: Mapping[str, Any],
    ) -> None:
        """Insert or update one serialized session."""
        await asyncio.to_thread(
            self._save_sync,
            session_data,
        )

    def _load_all_sync(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT payload
                FROM v3_sessions
                ORDER BY updated_at ASC
                """
            ).fetchall()

        return [
            json.loads(row["payload"])
            for row in rows
        ]

    async def load_sessions(self) -> list[dict[str, Any]]:
        """Load all persisted V3 sessions."""
        return await asyncio.to_thread(
            self._load_all_sync
        )

    def _delete_sync(self, session_id: str) -> None:
        with self._connect() as db:
            db.execute(
                """
                DELETE FROM v3_sessions
                WHERE session_id = ?
                """,
                (str(session_id),),
            )

    async def delete_session(self, session_id: str) -> None:
        """Delete one persisted session."""
        await asyncio.to_thread(
            self._delete_sync,
            session_id,
        )
