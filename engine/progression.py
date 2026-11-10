
"""
MHN ARCADE V3 - Player Progression

Independent V3 XP, levels, ranks, and leaderboard.
Uses the same isolated SQLite database as V3 achievements.
V2 progression data is never modified.
"""

from __future__ import annotations

import asyncio
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# =========================================================
# CONFIGURATION
# =========================================================

XP_FOR_PARTICIPATION = 20
XP_WIN_BONUS = 10
XP_DRAW_BONUS = 5

VALID_RESULTS = {"win", "loss", "draw"}

RANKS = (
    (500, "MYTHIC"),
    (300, "GRANDMASTER"),
    (175, "MANAGER"),
    (100, "MASTER"),
    (50, "ELITE"),
    (25, "PRO"),
    (10, "APPRENTICE"),
    (0, "ROOKIE"),
)


# =========================================================
# PROGRESSION MANAGER
# =========================================================

class V3ProgressionManager:
    """Manages V3 XP, levels, ranks, and player rankings."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        db = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 30000")
        db.execute("PRAGMA foreign_keys = ON")

        return db

    def _initialize_sync(self) -> None:
        with self._connect() as db:

            db.execute("""
                CREATE TABLE IF NOT EXISTS v3_player_progress (
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    total_xp INTEGER NOT NULL DEFAULT 0,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    draws INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS v3_processed_xp_rewards (
                    guild_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    xp_awarded INTEGER NOT NULL,
                    processed_at TEXT NOT NULL,
                    PRIMARY KEY (
                        guild_id,
                        session_id,
                        user_id
                    )
                )
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_v3_progress_leaderboard
                ON v3_player_progress (
                    guild_id,
                    total_xp DESC,
                    wins DESC
                )
            """)

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    # -----------------------------------------------------
    # LEVEL AND RANK CALCULATIONS
    # -----------------------------------------------------

    @staticmethod
    def xp_required_for_level(level: int) -> int:
        """XP required to advance from the given level."""

        level = max(1, int(level))

        return 100 + ((level - 1) * 25)

    @classmethod
    def calculate_level(cls, total_xp: int) -> dict[str, int]:
        """Convert lifetime XP into level and current-level XP."""

        remaining_xp = max(0, int(total_xp))
        level = 1

        while True:
            required = cls.xp_required_for_level(level)

            if remaining_xp < required:
                break

            remaining_xp -= required
            level += 1

        return {
            "level": level,
            "xp": remaining_xp,
            "xp_to_next_level": cls.xp_required_for_level(level),
        }

    @staticmethod
    def rank_for_level(level: int) -> str:
        level = max(1, int(level))

        for required_level, rank_name in RANKS:
            if level >= required_level:
                return rank_name

        return "ROOKIE"

    @classmethod
    def build_progress_data(
        cls,
        total_xp: int,
        games_played: int = 0,
        wins: int = 0,
        losses: int = 0,
        draws: int = 0,
    ) -> dict[str, Any]:

        total_xp = max(0, int(total_xp))
        level_data = cls.calculate_level(total_xp)

        return {
            "total_xp": total_xp,
            "lifetime_xp": total_xp,
            "level": level_data["level"],
            "xp": level_data["xp"],
            "xp_to_next_level": level_data["xp_to_next_level"],
            "rank": cls.rank_for_level(level_data["level"]),
            "games_played": int(games_played),
            "wins": int(wins),
            "losses": int(losses),
            "draws": int(draws),
        }

    # -----------------------------------------------------
    # XP REWARDS
    # -----------------------------------------------------

    @staticmethod
    def calculate_game_reward(result: str) -> int:
        result = str(result).lower()

        if result not in VALID_RESULTS:
            raise ValueError("Invalid game result.")

        reward = XP_FOR_PARTICIPATION

        if result == "win":
            reward += XP_WIN_BONUS

        elif result == "draw":
            reward += XP_DRAW_BONUS

        return reward

    def _record_completed_game_sync(
        self,
        session_data: dict[str, Any],
    ) -> list[dict[str, Any]]:

        guild_id = str(session_data["guild_id"])
        session_id = str(session_data["session_id"])
        players = session_data.get("players") or {}

        awarded: list[dict[str, Any]] = []

        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")

            for player_key, player in players.items():

                user_id = str(
                    player.get("user_id", player_key)
                )

                result = str(
                    player.get("result") or ""
                ).lower()

                if result not in VALID_RESULTS:
                    continue

                username = str(
                    player.get("username") or user_id
                )

                xp_reward = self.calculate_game_reward(result)

                inserted = db.execute(
                    """
                    INSERT OR IGNORE INTO
                    v3_processed_xp_rewards (
                        guild_id,
                        session_id,
                        user_id,
                        xp_awarded,
                        processed_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        session_id,
                        user_id,
                        xp_reward,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

                # This player already received XP for this session.
                if inserted.rowcount == 0:
                    continue

                db.execute(
                    """
                    INSERT INTO v3_player_progress (
                        guild_id,
                        user_id,
                        username,
                        total_xp,
                        games_played,
                        wins,
                        losses,
                        draws,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)

                    ON CONFLICT(guild_id, user_id)
                    DO UPDATE SET
                        username = excluded.username,
                        total_xp = total_xp + excluded.total_xp,
                        games_played = games_played + 1,
                        wins = wins + excluded.wins,
                        losses = losses + excluded.losses,
                        draws = draws + excluded.draws,
                        updated_at = excluded.updated_at
                    """,
                    (
                        guild_id,
                        user_id,
                        username,
                        xp_reward,
                        int(result == "win"),
                        int(result == "loss"),
                        int(result == "draw"),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

                row = db.execute(
                    """
                    SELECT total_xp, games_played,
                           wins, losses, draws
                    FROM v3_player_progress
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (guild_id, user_id),
                ).fetchone()

                progress = self.build_progress_data(
                    total_xp=row["total_xp"],
                    games_played=row["games_played"],
                    wins=row["wins"],
                    losses=row["losses"],
                    draws=row["draws"],
                )

                awarded.append({
                    "guild_id": guild_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "username": username,
                    "result": result,
                    "xp_awarded": xp_reward,
                    **progress,
                })

            db.commit()

        return awarded

    async def record_completed_game(
        self,
        session: Any,
    ) -> list[dict[str, Any]]:
        """Award XP once for every valid player in a completed session."""

        status = getattr(session, "status", None)
        status = getattr(status, "value", status)

        if status != "completed":
            return []

        players = getattr(session, "players", None)

        if not players:
            return []

        session_data = {
            "guild_id": str(session.guild_id),
            "session_id": str(session.session_id),
            "players": {},
        }

        for user_id, player in players.items():

            result = getattr(player, "result", None)

            if result not in VALID_RESULTS:
                return []

            session_data["players"][str(user_id)] = {
                "user_id": str(player.user_id),
                "username": str(player.username),
                "result": str(result),
            }

        return await asyncio.to_thread(
            self._record_completed_game_sync,
            session_data,
        )

    # -----------------------------------------------------
    # PLAYER PROGRESS
    # -----------------------------------------------------

    def _get_player_progress_sync(
        self,
        guild_id: str,
        user_id: str,
        username: str | None = None,
    ) -> dict[str, Any]:

        with self._connect() as db:
            row = db.execute(
                """
                SELECT username, total_xp,
                       games_played, wins, losses, draws
                FROM v3_player_progress
                WHERE guild_id = ? AND user_id = ?
                """,
                (str(guild_id), str(user_id)),
            ).fetchone()

        if row is None:
            return {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "username": username or str(user_id),
                **self.build_progress_data(0),
            }

        return {
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "username": row["username"],
            **self.build_progress_data(
                total_xp=row["total_xp"],
                games_played=row["games_played"],
                wins=row["wins"],
                losses=row["losses"],
                draws=row["draws"],
            ),
        }

    async def get_player_progress(
        self,
        guild_id: str | int,
        user_id: str | int,
        username: str | None = None,
    ) -> dict[str, Any]:

        return await asyncio.to_thread(
            self._get_player_progress_sync,
            str(guild_id),
            str(user_id),
            username,
        )

    # -----------------------------------------------------
    # LEADERBOARD
    # -----------------------------------------------------

    def _get_leaderboard_sync(
        self,
        guild_id: str,
        members: list[tuple[str, str]] | None,
        limit: int,
    ) -> list[dict[str, Any]]:

        with self._connect() as db:
            rows = db.execute(
                """
                SELECT user_id, username, total_xp,
                       games_played, wins, losses, draws
                FROM v3_player_progress
                WHERE guild_id = ?
                """,
                (str(guild_id),),
            ).fetchall()

        players: dict[str, dict[str, Any]] = {}

        for row in rows:
            user_id = str(row["user_id"])

            players[user_id] = {
                "guild_id": str(guild_id),
                "user_id": user_id,
                "username": row["username"],
                **self.build_progress_data(
                    total_xp=row["total_xp"],
                    games_played=row["games_played"],
                    wins=row["wins"],
                    losses=row["losses"],
                    draws=row["draws"],
                ),
            }

        # Add every supplied server member, including zero-XP members.
        if members is not None:
            for user_id, username in members:
                user_id = str(user_id)

                if user_id not in players:
                    players[user_id] = {
                        "guild_id": str(guild_id),
                        "user_id": user_id,
                        "username": str(username),
                        **self.build_progress_data(0),
                    }
                else:
                    players[user_id]["username"] = str(username)

        ordered = sorted(
            players.values(),
            key=lambda item: (
                item["total_xp"],
                item["wins"],
                item["games_played"],
                item["username"].lower(),
            ),
            reverse=True,
        )

        for position, player in enumerate(ordered, start=1):
            player["position"] = position

        return ordered[:limit] if limit > 0 else ordered

    async def get_leaderboard(
        self,
        guild_id: str | int,
        members: Iterable[Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Return the guild leaderboard.

        Pass guild.members to include members with zero XP.
        Bots are excluded automatically.
        """

        normalized_members = None

        if members is not None:
            normalized_members = []

            for member in members:
                if getattr(member, "bot", False):
                    continue

                user_id = getattr(member, "id", None)

                if user_id is None:
                    continue

                username = (
                    getattr(member, "display_name", None)
                    or getattr(member, "name", None)
                    or str(user_id)
                )

                normalized_members.append(
                    (str(user_id), str(username))
                )

        return await asyncio.to_thread(
            self._get_leaderboard_sync,
            str(guild_id),
            normalized_members,
            max(0, int(limit)),
        )
