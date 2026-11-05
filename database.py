"""
========================================================
MHN ARCADE V1
Database Core - Purple Gaming System 💜
========================================================
"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager


# ========================================================
# CONFIGURATION
# ========================================================

DB_PATH = Path(
    os.getenv("MHN_ARCADE_DB_PATH", "mhn_arcade.db")
)

SUPPORTED_LANGUAGES = ("ar", "en")


# ========================================================
# DATABASE CONNECTION
# ========================================================

@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ========================================================
# LEGACY DATABASE MIGRATION
# ========================================================

def archive_legacy_tables(db):
    """
    Preserve tables from the original prototype.
    Old tables are renamed instead of deleted.
    """

    legacy_tables = {
        "players": "players_legacy_v0",
        "achievements": "achievements_legacy_v0",
        "special_titles": "special_titles_legacy_v0"
    }

    for table, archive_name in legacy_tables.items():

        exists = db.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table,)
        ).fetchone()

        if not exists:
            continue

        columns = {
            row["name"]
            for row in db.execute(
                f"PRAGMA table_info({table})"
            )
        }

        if "guild_id" in columns:
            continue

        archive_exists = db.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (archive_name,)
        ).fetchone()

        if archive_exists:
            raise RuntimeError(
                f"Migration stopped: {table} and "
                f"{archive_name} both exist. "
                "Back up the database before proceeding."
            )

        db.execute(
            f"ALTER TABLE {table} RENAME TO {archive_name}"
        )


# ========================================================
# INITIALIZE DATABASE
# ========================================================

def initialize_database():

    with get_connection() as db:

        archive_legacy_tables(db)

        db.executescript(
            """

            CREATE TABLE IF NOT EXISTS players (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                active_language TEXT,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );


            CREATE TABLE IF NOT EXISTS progress (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                language TEXT NOT NULL
                    CHECK(language IN ('ar', 'en')),

                level INTEGER NOT NULL DEFAULT 0
                    CHECK(level BETWEEN 0 AND 500),

                xp INTEGER NOT NULL DEFAULT 0
                    CHECK(xp >= 0),

                lifetime_xp INTEGER NOT NULL DEFAULT 0
                    CHECK(lifetime_xp >= 0),

                prestige INTEGER NOT NULL DEFAULT 0
                    CHECK(prestige >= 0),

                games_played INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,

                current_streak INTEGER NOT NULL DEFAULT 0,
                best_streak INTEGER NOT NULL DEFAULT 0,

                favorite_game TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (guild_id, user_id, language),

                FOREIGN KEY (guild_id, user_id)
                    REFERENCES players(guild_id, user_id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS achievements (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                language TEXT NOT NULL
                    CHECK(language IN ('ar', 'en')),

                achievement_key TEXT NOT NULL,
                unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (
                    guild_id,
                    user_id,
                    language,
                    achievement_key
                ),

                FOREIGN KEY (
                    guild_id,
                    user_id,
                    language
                )
                REFERENCES progress(
                    guild_id,
                    user_id,
                    language
                )
                ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS special_titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TEXT DEFAULT CURRENT_TIMESTAMP
            );


            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                language TEXT NOT NULL
                    CHECK(language IN ('ar', 'en')),

                name TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'ended')),

                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                started_by TEXT NOT NULL,
                ended_by TEXT
            );


            CREATE UNIQUE INDEX IF NOT EXISTS
            one_active_season_per_language

            ON seasons(guild_id, language)

            WHERE status = 'active';


            CREATE TABLE IF NOT EXISTS season_stats (
                season_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                games_played INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (season_id, user_id),

                FOREIGN KEY (season_id)
                    REFERENCES seasons(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS season_results (
                season_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                games_played INTEGER NOT NULL DEFAULT 0,
                final_level INTEGER NOT NULL DEFAULT 0,
                final_rank TEXT NOT NULL DEFAULT 'ROOKIE',

                PRIMARY KEY (season_id, user_id),

                FOREIGN KEY (season_id)
                    REFERENCES seasons(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS bot_messages (
                guild_id TEXT NOT NULL,
                message_key TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (guild_id, message_key)
            );


            CREATE INDEX IF NOT EXISTS
            progress_leaderboard_idx

            ON progress(
                guild_id,
                language,
                level DESC,
                xp DESC
            );

            """
        )

    print("💜 MHN ARCADE database initialized successfully!")


# ========================================================
# PLAYER REGISTRATION
# ========================================================

def create_player(guild_id, user_id, username):

    with get_connection() as db:

        db.execute(
            """
            INSERT INTO players (
                guild_id,
                user_id,
                username
            )
            VALUES (?, ?, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                username = excluded.username,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                str(guild_id),
                str(user_id),
                username
            )
        )


# ========================================================
# GET PLAYER
# ========================================================

def get_player(guild_id, user_id):

    with get_connection() as db:

        return db.execute(
            """
            SELECT *
            FROM players
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                str(guild_id),
                str(user_id)
            )
        ).fetchone()


# ========================================================
# CREATE LANGUAGE PROGRESS
# ========================================================

def ensure_progress(guild_id, user_id, language):

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language.")

    with get_connection() as db:

        db.execute(
            """
            INSERT OR IGNORE INTO progress (
                guild_id,
                user_id,
                language
            )
            VALUES (?, ?, ?)
            """,
            (
                str(guild_id),
                str(user_id),
                language
            )
        )


# ========================================================
# GET PLAYER PROGRESS
# ========================================================

def get_progress(guild_id, user_id, language):

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language.")

    with get_connection() as db:

        return db.execute(
            """
            SELECT *
            FROM progress
            WHERE guild_id = ?
            AND user_id = ?
            AND language = ?
            """,
            (
                str(guild_id),
                str(user_id),
                language
            )
        ).fetchone()


# ========================================================
# SELECT LANGUAGE
# ========================================================

def select_language(
    guild_id,
    user_id,
    username,
    language
):

    """
    First selection:
        Creates a new progress track.

    Language switch:
        Resets both language progress tracks.
        Resets this player's stats in active seasons.
        Keeps ended season archives.
        Keeps owner-granted special titles.
    """

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language.")

    guild_id = str(guild_id)
    user_id = str(user_id)

    with get_connection() as db:

        db.execute(
            """
            INSERT INTO players (
                guild_id,
                user_id,
                username
            )
            VALUES (?, ?, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                username = excluded.username,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                guild_id,
                user_id,
                username
            )
        )

        player = db.execute(
            """
            SELECT active_language
            FROM players
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                guild_id,
                user_id
            )
        ).fetchone()

        previous_language = player["active_language"]

        switched = (
            previous_language is not None
            and previous_language != language
        )

        if switched:

            # Delete both language progress tracks.
            # Related achievements are deleted automatically.
            db.execute(
                """
                DELETE FROM progress
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    guild_id,
                    user_id
                )
            )

            # Reset only this player's stats in active seasons.
            # Ended season results and archives remain untouched.
            db.execute(
                """
                DELETE FROM season_stats
                WHERE user_id = ?
                AND season_id IN (
                    SELECT id
                    FROM seasons
                    WHERE guild_id = ?
                    AND language IN ('ar', 'en')
                    AND status = 'active'
                )
                """,
                (
                    user_id,
                    guild_id
                )
            )

        # Create a fresh track for the selected language.
        db.execute(
            """
            INSERT OR IGNORE INTO progress (
                guild_id,
                user_id,
                language
            )
            VALUES (?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                language
            )
        )

        db.execute(
            """
            UPDATE players
            SET active_language = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                language,
                guild_id,
                user_id
            )
        )

    return switched, language


# ========================================================
# UPDATE PLAYER USERNAME
# ========================================================

def update_username(guild_id, user_id, username):

    with get_connection() as db:

        db.execute(
            """
            UPDATE players
            SET username = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                username,
                str(guild_id),
                str(user_id)
            )
        )


# ========================================================
# SAVE PERSISTENT BOT MESSAGE
# ========================================================

def save_bot_message(
    guild_id,
    message_key,
    channel_id,
    message_id
):

    with get_connection() as db:

        db.execute(
            """
            INSERT INTO bot_messages (
                guild_id,
                message_key,
                channel_id,
                message_id
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(guild_id, message_key)
            DO UPDATE SET
                channel_id = excluded.channel_id,
                message_id = excluded.message_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                str(guild_id),
                message_key,
                str(channel_id),
                str(message_id)
            )
        )


# ========================================================
# GET PERSISTENT BOT MESSAGE
# ========================================================

def get_bot_message(guild_id, message_key):

    with get_connection() as db:

        return db.execute(
            """
            SELECT *
            FROM bot_messages
            WHERE guild_id = ?
            AND message_key = ?
            """,
            (
                str(guild_id),
                message_key
            )
        ).fetchone()


# ========================================================
# GET ACTIVE SEASON
# ========================================================

def get_active_season(guild_id, language):

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language.")

    with get_connection() as db:

        return db.execute(
            """
            SELECT *
            FROM seasons
            WHERE guild_id = ?
            AND language = ?
            AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                str(guild_id),
                language
            )
        ).fetchone()


# ========================================================
# DATABASE HEALTH CHECK
# ========================================================

def database_health_check():

    try:

        with get_connection() as db:

            result = db.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            return result[0] == "ok"

    except sqlite3.Error:

        return False
