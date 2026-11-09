
"""
MHN ARCADE V3 - Achievement System

Independent V3 achievements and statistics.
Uses the V3 SQLite database only.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACHIEVEMENTS = {
    "break_the_barrier": {
        "name_ar": "كسر الحاجز",
        "name_en": "Break the Barrier",
        "description_ar": "أكمل 10 ألعاب.",
        "description_en": "Complete 10 games.",
        "rarity": "Uncommon",
    },
    "first_crown": {
        "name_ar": "أول تتويج",
        "name_en": "First Crown",
        "description_ar": "حقق الفوز في 5 ألعاب.",
        "description_en": "Win 5 games.",
        "rarity": "Rare",
    },
    "unstoppable": {
        "name_ar": "لا يعرف التوقف",
        "name_en": "Unstoppable",
        "description_ar": "أكمل 25 لعبة.",
        "description_en": "Complete 25 games.",
        "rarity": "Rare",
    },
    "team_spirit": {
        "name_ar": "روح الفريق",
        "name_en": "Team Spirit",
        "description_ar": "شارك في 10 ألعاب جماعية مكتملة.",
        "description_en": "Participate in 10 completed multiplayer games.",
        "rarity": "Epic",
    },
    "proof_of_presence": {
        "name_ar": "إثبات الوجود",
        "name_en": "Proof of Presence",
        "description_ar": "حقق 10 انتصارات موزعة على 3 أنواع ألعاب مختلفة.",
        "description_en": "Earn 10 wins across 3 different game types.",
        "rarity": "Epic",
    },
}


class V3AchievementManager:
    """Tracks V3 game results, player statistics, and achievements."""

    VALID_RESULTS = {"win", "loss", "draw"}

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 30000")
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _initialize_sync(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS v3_player_stats (
                    user_id TEXT PRIMARY KEY,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    multiplayer_games INTEGER NOT NULL DEFAULT 0,
                    game_type_wins TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS v3_player_achievements (
                    user_id TEXT NOT NULL,
                    achievement_id TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS v3_processed_game_results (
                    session_id TEXT PRIMARY KEY,
                    processed_at TEXT NOT NULL
                )
            """)

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    @staticmethod
    def _get_session_value(session: Any, name: str) -> Any:
        value = getattr(session, name, None)
        return getattr(value, "value", value)

    @staticmethod
    def _get_eligible_achievements(
        stats: dict[str, Any],
    ) -> list[str]:

        game_type_wins = stats["game_type_wins"]

        total_type_wins = sum(
            int(value) for value in game_type_wins.values()
        )

        different_winning_games = sum(
            1 for value in game_type_wins.values()
            if int(value) > 0
        )

        eligible = []

        if stats["games_played"] >= 10:
            eligible.append("break_the_barrier")

        if stats["wins"] >= 5:
            eligible.append("first_crown")

        if stats["games_played"] >= 25:
            eligible.append("unstoppable")

        if stats["multiplayer_games"] >= 10:
            eligible.append("team_spirit")

        if (
            total_type_wins >= 10
            and different_winning_games >= 3
        ):
            eligible.append("proof_of_presence")

        return eligible

    def _record_sync(
        self,
        session_data: dict[str, Any],
    ) -> list[dict[str, str]]:

        session_id = str(session_data["session_id"])
        game_id = str(session_data["game_id"])
        metadata = session_data.get("metadata") or {}
        players = session_data.get("players") or {}

        is_multiplayer = (
            metadata.get("game_mode") == "multiplayer"
            or len(players) > 1
        )

        unlocked: list[dict[str, str]] = []

        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")

            inserted = db.execute(
                """
                INSERT OR IGNORE INTO v3_processed_game_results
                (session_id, processed_at)
                VALUES (?, ?)
                """,
                (
                    session_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            # This session has already been counted.
            if inserted.rowcount == 0:
                db.rollback()
                return []

            for user_id, player in players.items():
                user_id = str(
                    player.get("user_id", user_id)
                )

                result = str(
                    player.get("result") or ""
                ).lower()

                if result not in self.VALID_RESULTS:
                    continue

                row = db.execute(
                    """
                    SELECT games_played, wins,
                           multiplayer_games, game_type_wins
                    FROM v3_player_stats
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()

                if row is None:
                    stats = {
                        "games_played": 0,
                        "wins": 0,
                        "multiplayer_games": 0,
                        "game_type_wins": {},
                    }
                else:
                    stats = {
                        "games_played": int(row["games_played"]),
                        "wins": int(row["wins"]),
                        "multiplayer_games": int(
                            row["multiplayer_games"]
                        ),
                        "game_type_wins": json.loads(
                            row["game_type_wins"] or "{}"
                        ),
                    }

                stats["games_played"] += 1

                if is_multiplayer:
                    stats["multiplayer_games"] += 1

                if result == "win":
                    stats["wins"] += 1
                    stats["game_type_wins"][game_id] = (
                        int(stats["game_type_wins"].get(game_id, 0))
                        + 1
                    )

                db.execute(
                    """
                    INSERT INTO v3_player_stats (
                        user_id,
                        games_played,
                        wins,
                        multiplayer_games,
                        game_type_wins,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)

                    ON CONFLICT(user_id)
                    DO UPDATE SET
                        games_played = excluded.games_played,
                        wins = excluded.wins,
                        multiplayer_games = excluded.multiplayer_games,
                        game_type_wins = excluded.game_type_wins,
                        updated_at = excluded.updated_at
                    """,
                    (
                        user_id,
                        stats["games_played"],
                        stats["wins"],
                        stats["multiplayer_games"],
                        json.dumps(
                            stats["game_type_wins"],
                            ensure_ascii=False,
                        ),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

                eligible = self._get_eligible_achievements(stats)

                for achievement_id in eligible:
                    definition = ACHIEVEMENTS[achievement_id]

                    result_insert = db.execute(
                        """
                        INSERT OR IGNORE INTO
                        v3_player_achievements (
                            user_id,
                            achievement_id,
                            unlocked_at
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            user_id,
                            achievement_id,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    if result_insert.rowcount == 1:
                        unlocked.append({
                            "user_id": user_id,
                            "username": str(
                                player.get("username", user_id)
                            ),
                            "achievement_id": achievement_id,
                            **definition,
                        })

            db.commit()

        return unlocked

    async def record_completed_game(
        self,
        session: Any,
    ) -> list[dict[str, str]]:

        status = self._get_session_value(session, "status")

        if status != "completed":
            return []

        players = getattr(session, "players", {})

        if not players:
            return []

        for player in players.values():
            if getattr(player, "result", None) not in self.VALID_RESULTS:
                return []

        data = {
            "session_id": str(session.session_id),
            "game_id": str(session.game_id),
            "status": status,
            "metadata": dict(session.metadata or {}),
            "players": {
                str(user_id): {
                    "user_id": str(player.user_id),
                    "username": str(player.username),
                    "result": str(player.result),
                }
                for user_id, player in players.items()
            },
        }

        return await asyncio.to_thread(
            self._record_sync,
            data,
        )

    def _get_player_stats_sync(
        self,
        user_id: str,
    ) -> dict[str, Any]:

        with self._connect() as db:
            row = db.execute(
                """
                SELECT games_played, wins,
                       multiplayer_games, game_type_wins
                FROM v3_player_stats
                WHERE user_id = ?
                """,
                (str(user_id),),
            ).fetchone()

            achievements = db.execute(
                """
                SELECT achievement_id, unlocked_at
                FROM v3_player_achievements
                WHERE user_id = ?
                ORDER BY unlocked_at ASC
                """,
                (str(user_id),),
            ).fetchall()

        if row is None:
            stats = {
                "games_played": 0,
                "wins": 0,
                "multiplayer_games": 0,
                "game_type_wins": {},
            }
        else:
            stats = {
                "games_played": int(row["games_played"]),
                "wins": int(row["wins"]),
                "multiplayer_games": int(row["multiplayer_games"]),
                "game_type_wins": json.loads(
                    row["game_type_wins"] or "{}"
                ),
            }

        stats["achievements"] = [
            {
                "achievement_id": item["achievement_id"],
                "unlocked_at": item["unlocked_at"],
                **ACHIEVEMENTS[item["achievement_id"]],
            }
            for item in achievements
            if item["achievement_id"] in ACHIEVEMENTS
        ]

        return stats

    async def get_player_stats(
        self,
        user_id: str | int,
    ) -> dict[str, Any]:

        return await asyncio.to_thread(
            self._get_player_stats_sync,
            str(user_id),
        )
