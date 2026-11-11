
"""
MHN ARCADE V3 - Trophy and Achievement System

- Preserves existing trophy records.
- Expands the collection to 18 trophies.
- Uses V3 game statistics and V3 progression XP.
- Applies both level and gameplay requirements.
- Keeps the existing SQLite database structure compatible.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =========================================================
# TROPHY TIERS
# =========================================================

TROPHY_TIERS = {
    "Common": {
        "name_ar": "شائع",
        "level_range": "1–9",
        "rank_ar": "مبتدئ",
        "rank_en": "ROOKIE",
        "level_min": 1,
    },
    "Uncommon": {
        "name_ar": "غير شائع",
        "level_range": "10–24",
        "rank_ar": "متدرب",
        "rank_en": "APPRENTICE",
        "level_min": 10,
    },
    "Rare": {
        "name_ar": "نادر",
        "level_range": "25–49",
        "rank_ar": "محترف",
        "rank_en": "PRO",
        "level_min": 25,
    },
    "Very Rare": {
        "name_ar": "نادر جداً",
        "level_range": "50–99",
        "rank_ar": "نخبة",
        "rank_en": "ELITE",
        "level_min": 50,
    },
    "Legendary": {
        "name_ar": "أسطوري",
        "level_range": "100–299",
        "rank_ar": "ماستر / مانجر",
        "rank_en": "MASTER / MANAGER",
        "level_min": 100,
    },
    "Platinum": {
        "name_ar": "بلاتيني",
        "level_range": "300+",
        "rank_ar": "جراند ماستر / ميثك",
        "rank_en": "GRANDMASTER / MYTHIC",
        "level_min": 300,
    },
}


# =========================================================
# TROPHY COLLECTION
# =========================================================

# Existing trophy IDs are intentionally preserved.
# Previously unlocked trophies will remain unlocked.

ACHIEVEMENTS = {

    # -----------------------------------------------------
    # COMMON — LEVEL 1+
    # -----------------------------------------------------

    "first_steps": {
        "name_ar": "أول خطوة",
        "name_en": "First Steps",
        "description_ar": "أكمل أول لعبة لك.",
        "description_en": "Complete your first game.",
        "rarity": "Common",
        "min_level": 1,
        "games_required": 1,
    },

    "warming_up": {
        "name_ar": "بداية الحماس",
        "name_en": "Warming Up",
        "description_ar": "أكمل 3 ألعاب.",
        "description_en": "Complete 3 games.",
        "rarity": "Common",
        "min_level": 1,
        "games_required": 3,
    },

    "first_victory": {
        "name_ar": "أول انتصار",
        "name_en": "First Victory",
        "description_ar": "حقق أول فوز لك.",
        "description_en": "Earn your first victory.",
        "rarity": "Common",
        "min_level": 1,
        "wins_required": 1,
    },

    # -----------------------------------------------------
    # UNCOMMON — LEVEL 10+
    # -----------------------------------------------------

    "break_the_barrier": {
        "name_ar": "كسر الحاجز",
        "name_en": "Break the Barrier",
        "description_ar": "أكمل 10 ألعاب.",
        "description_en": "Complete 10 games.",
        "rarity": "Uncommon",
        "min_level": 10,
        "games_required": 10,
    },

    "dedicated_player": {
        "name_ar": "لاعب ملتزم",
        "name_en": "Dedicated Player",
        "description_ar": "أكمل 15 لعبة.",
        "description_en": "Complete 15 games.",
        "rarity": "Uncommon",
        "min_level": 10,
        "games_required": 15,
    },

    "game_regular": {
        "name_ar": "وجه معروف",
        "name_en": "Regular Player",
        "description_ar": "أكمل 20 لعبة.",
        "description_en": "Complete 20 games.",
        "rarity": "Uncommon",
        "min_level": 10,
        "games_required": 20,
    },

    # -----------------------------------------------------
    # RARE — LEVEL 25+
    # -----------------------------------------------------

    "first_crown": {
        "name_ar": "أول تتويج",
        "name_en": "First Crown",
        "description_ar": "حقق الفوز في 5 ألعاب.",
        "description_en": "Win 5 games.",
        "rarity": "Rare",
        "min_level": 25,
        "wins_required": 5,
    },

    "unstoppable": {
        "name_ar": "لا يعرف التوقف",
        "name_en": "Unstoppable",
        "description_ar": "أكمل 25 لعبة.",
        "description_en": "Complete 25 games.",
        "rarity": "Rare",
        "min_level": 25,
        "games_required": 25,
    },

    "rising_champion": {
        "name_ar": "بطل صاعد",
        "name_en": "Rising Champion",
        "description_ar": "حقق الفوز في 25 لعبة.",
        "description_en": "Win 25 games.",
        "rarity": "Rare",
        "min_level": 25,
        "wins_required": 25,
    },

    # -----------------------------------------------------
    # VERY RARE — LEVEL 50+
    # -----------------------------------------------------

    "team_spirit": {
        "name_ar": "روح الفريق",
        "name_en": "Team Spirit",
        "description_ar": "شارك في 10 ألعاب جماعية مكتملة.",
        "description_en": "Participate in 10 completed multiplayer games.",
        "rarity": "Very Rare",
        "min_level": 50,
        "multiplayer_required": 10,
    },

    "proof_of_presence": {
        "name_ar": "إثبات الوجود",
        "name_en": "Proof of Presence",
        "description_ar": "حقق 10 انتصارات موزعة على 3 أنواع ألعاب مختلفة.",
        "description_en": "Earn 10 wins across 3 different game types.",
        "rarity": "Very Rare",
        "min_level": 50,
        "wins_required": 10,
        "game_types_required": 3,
    },

    "veteran_player": {
        "name_ar": "لاعب مخضرم",
        "name_en": "Veteran Player",
        "description_ar": "أكمل 50 لعبة.",
        "description_en": "Complete 50 games.",
        "rarity": "Very Rare",
        "min_level": 50,
        "games_required": 50,
    },

    # -----------------------------------------------------
    # LEGENDARY — LEVEL 100+
    # -----------------------------------------------------

    "arcade_master": {
        "name_ar": "سيد الأركيد",
        "name_en": "Arcade Master",
        "description_ar": "أكمل 100 لعبة.",
        "description_en": "Complete 100 games.",
        "rarity": "Legendary",
        "min_level": 100,
        "games_required": 100,
    },

    "champions_legacy": {
        "name_ar": "إرث الأبطال",
        "name_en": "Champion's Legacy",
        "description_ar": "حقق الفوز في 50 لعبة.",
        "description_en": "Win 50 games.",
        "rarity": "Legendary",
        "min_level": 100,
        "wins_required": 50,
    },

    "multiplayer_legend": {
        "name_ar": "أسطورة الجماعة",
        "name_en": "Multiplayer Legend",
        "description_ar": "شارك في 50 لعبة جماعية مكتملة.",
        "description_en": "Participate in 50 completed multiplayer games.",
        "rarity": "Legendary",
        "min_level": 100,
        "multiplayer_required": 50,
    },

    # -----------------------------------------------------
    # PLATINUM — LEVEL 300+
    # -----------------------------------------------------

    "arcade_immortal": {
        "name_ar": "خلود الأركيد",
        "name_en": "Arcade Immortal",
        "description_ar": "أكمل 200 لعبة.",
        "description_en": "Complete 200 games.",
        "rarity": "Platinum",
        "min_level": 300,
        "games_required": 200,
    },

    "undisputed_champion": {
        "name_ar": "البطل بلا منازع",
        "name_en": "Undisputed Champion",
        "description_ar": "حقق الفوز في 100 لعبة.",
        "description_en": "Win 100 games.",
        "rarity": "Platinum",
        "min_level": 300,
        "wins_required": 100,
    },

    "community_grandmaster": {
        "name_ar": "جراند ماستر المجتمع",
        "name_en": "Community Grandmaster",
        "description_ar": "شارك في 100 لعبة جماعية مكتملة.",
        "description_en": "Participate in 100 completed multiplayer games.",
        "rarity": "Platinum",
        "min_level": 300,
        "multiplayer_required": 100,
    },
}


# =========================================================
# ACHIEVEMENT MANAGER
# =========================================================

class V3AchievementManager:
    """Tracks V3 game results, player statistics, and trophies."""

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

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # LEVEL CALCULATION
    # -----------------------------------------------------

    @staticmethod
    def _calculate_level(total_xp: int) -> int:
        remaining_xp = max(0, int(total_xp))
        level = 1

        while True:
            required_xp = 100 + ((level - 1) * 25)

            if remaining_xp < required_xp:
                return level

            remaining_xp -= required_xp
            level += 1

    @classmethod
    def _get_player_level_sync(
        cls,
        db: sqlite3.Connection,
        guild_id: str,
        user_id: str,
    ) -> int:

        row = db.execute(
            """
            SELECT total_xp
            FROM v3_player_progress
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(guild_id), str(user_id)),
        ).fetchone()

        if row is None:
            return 1

        return cls._calculate_level(row["total_xp"])

    # -----------------------------------------------------
    # TROPHY REQUIREMENTS
    # -----------------------------------------------------

    @staticmethod
    def _get_eligible_achievements(
        stats: dict[str, Any],
        level: int,
    ) -> list[str]:

        game_type_wins = stats["game_type_wins"]

        different_winning_games = sum(
            1
            for value in game_type_wins.values()
            if int(value) > 0
        )

        eligible = []

        for achievement_id, definition in ACHIEVEMENTS.items():

            if level < int(definition.get("min_level", 1)):
                continue

            if stats["games_played"] < int(
                definition.get("games_required", 0)
            ):
                continue

            if stats["wins"] < int(
                definition.get("wins_required", 0)
            ):
                continue

            if stats["multiplayer_games"] < int(
                definition.get("multiplayer_required", 0)
            ):
                continue

            if different_winning_games < int(
                definition.get("game_types_required", 0)
            ):
                continue

            eligible.append(achievement_id)

        return eligible

    # -----------------------------------------------------
    # COMPLETED GAME PROCESSING
    # -----------------------------------------------------

    def _record_sync(
        self,
        session_data: dict[str, Any],
    ) -> list[dict[str, str]]:

        session_id = str(session_data["session_id"])
        guild_id = str(session_data["guild_id"])
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

            # Prevent duplicate game counting.
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
                        int(
                            stats["game_type_wins"].get(
                                game_id,
                                0,
                            )
                        ) + 1
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

                # XP is processed by V3ProgressionManager first.
                # Read the updated level before evaluating trophies.
                level = self._get_player_level_sync(
                    db,
                    guild_id,
                    user_id,
                )

                eligible = self._get_eligible_achievements(
                    stats,
                    level,
                )

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

        status = getattr(session, "status", None)
        status = getattr(status, "value", status)

        if status != "completed":
            return []

        players = getattr(session, "players", {})

        if not players:
            return []

        for player in players.values():

            result = getattr(player, "result", None)

            if result not in self.VALID_RESULTS:
                return []

        data = {
            "guild_id": str(session.guild_id),
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

    # -----------------------------------------------------
    # PLAYER STATISTICS
    # -----------------------------------------------------

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
