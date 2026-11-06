"""
========================================================
MHN ARCADE V2.0
Database Core - Purple Gaming System 💜
========================================================

- يحافظ على بيانات قاعدة البيانات الحالية.
- لا يحذف بيانات اللاعبين أو المواسم أو الإنجازات.
- يدعم ترحيل الجداول القديمة بأمان.
- يدعم XP والمستويات حتى Level 500.
- يدعم العملات والمحفظة والبنك.
- يدعم إحصائيات الألعاب والمواسم.
========================================================
"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager


# ========================================================
# CONFIGURATION
# ========================================================

DB_PATH = Path(os.getenv("MHN_ARCADE_DB_PATH", "mhn_arcade.db"))

SUPPORTED_LANGUAGES = ("ar", "en")

STARTING_COINS = 100
MAX_LEVEL = 500


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
# INTERNAL HELPERS
# ========================================================

def _validate_language(language):
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language.")


def _ensure_player(db, guild_id, user_id, username):
    db.execute(
        """
        INSERT INTO players (
            guild_id, user_id, username
        )
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET
            username = excluded.username,
            updated_at = CURRENT_TIMESTAMP
        """,
        (str(guild_id), str(user_id), str(username))
    )

    db.execute(
        """
        INSERT OR IGNORE INTO wallets (
            guild_id, user_id, coins
        )
        VALUES (?, ?, ?)
        """,
        (str(guild_id), str(user_id), STARTING_COINS)
    )


def _ensure_progress(db, guild_id, user_id, language):
    _validate_language(language)

    db.execute(
        """
        INSERT OR IGNORE INTO progress (
            guild_id, user_id, language
        )
        VALUES (?, ?, ?)
        """,
        (str(guild_id), str(user_id), language)
    )


def _ensure_wallet(db, guild_id, user_id):
    guild_id = str(guild_id)
    user_id = str(user_id)

    player = db.execute(
        """
        SELECT 1
        FROM players
        WHERE guild_id = ? AND user_id = ?
        """,
        (guild_id, user_id)
    ).fetchone()

    if player is None:
        _ensure_player(db, guild_id, user_id, user_id)

    db.execute(
        """
        INSERT OR IGNORE INTO wallets (
            guild_id, user_id, coins
        )
        VALUES (?, ?, ?)
        """,
        (guild_id, user_id, STARTING_COINS)
    )


def _get_wallet_dict(db, guild_id, user_id):
    row = db.execute(
        """
        SELECT coins, bank
        FROM wallets
        WHERE guild_id = ? AND user_id = ?
        """,
        (str(guild_id), str(user_id))
    ).fetchone()

    return dict(row) if row else {
        "coins": STARTING_COINS,
        "bank": 0
    }


def _apply_xp(db, guild_id, user_id, language, amount):
    _ensure_progress(db, guild_id, user_id, language)

    row = db.execute(
        """
        SELECT level, xp, lifetime_xp
        FROM progress
        WHERE guild_id = ? AND user_id = ? AND language = ?
        """,
        (str(guild_id), str(user_id), language)
    ).fetchone()

    level = int(row["level"])
    xp = int(row["xp"]) + amount
    lifetime_xp = int(row["lifetime_xp"]) + amount

    levels_gained = 0

    while level < MAX_LEVEL:
        required = xp_required_for_next_level(level)

        if xp < required:
            break

        xp -= required
        level += 1
        levels_gained += 1

    if level >= MAX_LEVEL:
        xp = min(
            xp,
            xp_required_for_next_level(level) - 1
        )

    db.execute(
        """
        UPDATE progress
        SET level = ?,
            xp = ?,
            lifetime_xp = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE guild_id = ? AND user_id = ? AND language = ?
        """,
        (
            level,
            xp,
            lifetime_xp,
            str(guild_id),
            str(user_id),
            language
        )
    )

    return {
        "level": level,
        "xp": xp,
        "lifetime_xp": lifetime_xp,
        "levels_gained": levels_gained,
        "next_level_xp": xp_required_for_next_level(level)
    }


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
                f"Migration stopped: {table} and {archive_name} "
                "both exist. Back up the database before proceeding."
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

                FOREIGN KEY (guild_id, user_id, language)
                    REFERENCES progress(guild_id, user_id, language)
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

            CREATE INDEX IF NOT EXISTS progress_leaderboard_idx
            ON progress(guild_id, language, level DESC, xp DESC);

            CREATE TABLE IF NOT EXISTS wallets (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                coins INTEGER NOT NULL DEFAULT 100
                    CHECK(coins >= 0),
                bank INTEGER NOT NULL DEFAULT 0
                    CHECK(bank >= 0),
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id),
                FOREIGN KEY (guild_id, user_id)
                    REFERENCES players(guild_id, user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS selected_characters (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                character_id TEXT NOT NULL,
                selected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id),
                FOREIGN KEY (guild_id, user_id)
                    REFERENCES players(guild_id, user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS game_stats (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                games_played INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                best_score INTEGER NOT NULL DEFAULT 0,
                total_score INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, game_id),
                FOREIGN KEY (guild_id, user_id)
                    REFERENCES players(guild_id, user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS wallet_history_idx
            ON wallet_transactions(guild_id, user_id, id DESC);

            CREATE INDEX IF NOT EXISTS game_stats_leaderboard_idx
            ON game_stats(guild_id, game_id, wins DESC);
            """
        )

    print("💜 MHN ARCADE V2.0 database initialized successfully!")


# ========================================================
# PLAYER REGISTRATION
# ========================================================

def create_player(guild_id, user_id, username):

    with get_connection() as db:
        _ensure_player(
            db,
            str(guild_id),
            str(user_id),
            str(username)
        )


def get_player(guild_id, user_id):

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM players
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(guild_id), str(user_id))
        ).fetchone()


def update_username(guild_id, user_id, username):

    with get_connection() as db:
        db.execute(
            """
            UPDATE players
            SET username = ?, updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(username), str(guild_id), str(user_id))
        )


# ========================================================
# PLAYER PROGRESS
# ========================================================

def ensure_progress(guild_id, user_id, language):

    _validate_language(language)

    with get_connection() as db:
        _ensure_progress(db, guild_id, user_id, language)


def get_progress(guild_id, user_id, language):

    _validate_language(language)

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM progress
            WHERE guild_id = ? AND user_id = ? AND language = ?
            """,
            (str(guild_id), str(user_id), language)
        ).fetchone()


def select_language(guild_id, user_id, username, language):
    """
    First selection creates a progress track.

    Switching language resets both language progress tracks
    and active season stats, while keeping ended seasons,
    wallet, character selection and owner-granted titles.
    """

    _validate_language(language)

    guild_id = str(guild_id)
    user_id = str(user_id)

    with get_connection() as db:

        _ensure_player(db, guild_id, user_id, username)

        player = db.execute(
            """
            SELECT active_language
            FROM players
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id)
        ).fetchone()

        previous_language = player["active_language"]

        switched = (
            previous_language is not None
            and previous_language != language
        )

        if switched:

            db.execute(
                """
                DELETE FROM progress
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, user_id)
            )

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
                (user_id, guild_id)
            )

        _ensure_progress(db, guild_id, user_id, language)

        db.execute(
            """
            UPDATE players
            SET active_language = ?, updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ?
            """,
            (language, guild_id, user_id)
        )

    return switched, language


# ========================================================
# XP SYSTEM
# ========================================================

def xp_required_for_next_level(level):
    """XP required to advance from the supplied level."""

    level = max(0, int(level))
    return 100 + (level * 25)


def award_xp(guild_id, user_id, language, amount):
    """
    Adds XP and calculates level-ups.
    Returns a dictionary with the updated progress.
    """

    _validate_language(language)

    amount = max(0, int(amount))

    with get_connection() as db:

        _ensure_progress(db, guild_id, user_id, language)

        return _apply_xp(
            db,
            guild_id,
            user_id,
            language,
            amount
        )


# ========================================================
# GAME RESULT TRACKING
# ========================================================

def record_game_result(
    guild_id,
    user_id,
    username,
    language,
    game_id,
    result="draw",
    xp_reward=0,
    coin_reward=0,
    score=0
):
    """
    Records one completed game atomically.

    result must be: win, loss, or draw.

    All related updates are saved in one transaction:
    - Game statistics
    - Player progress and streaks
    - XP and level-ups
    - Wallet rewards
    - Active season statistics

    A zero-coin reward is valid and does not create
    a wallet transaction.
    """

    _validate_language(language)

    if result not in ("win", "loss", "draw"):
        raise ValueError("Invalid game result.")

    game_id = str(game_id).strip()

    if not game_id:
        raise ValueError("Game ID cannot be empty.")

    xp_reward = max(0, int(xp_reward))
    coin_reward = max(0, int(coin_reward))
    score = max(0, int(score))

    guild_id = str(guild_id)
    user_id = str(user_id)
    username = str(username)

    with get_connection() as db:

        # Ensure player, wallet and progress exist.
        _ensure_player(
            db,
            guild_id,
            user_id,
            username
        )

        _ensure_progress(
            db,
            guild_id,
            user_id,
            language
        )

        # Update per-game statistics.
        db.execute(
            """
            INSERT INTO game_stats (
                guild_id,
                user_id,
                game_id,
                games_played,
                wins,
                losses,
                draws,
                best_score,
                total_score
            )
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)

            ON CONFLICT(guild_id, user_id, game_id)
            DO UPDATE SET
                games_played = games_played + 1,
                wins = wins + excluded.wins,
                losses = losses + excluded.losses,
                draws = draws + excluded.draws,
                best_score = MAX(best_score, excluded.best_score),
                total_score = total_score + excluded.total_score,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                guild_id,
                user_id,
                game_id,
                int(result == "win"),
                int(result == "loss"),
                int(result == "draw"),
                score,
                score
            )
        )

        # Update streaks.
        progress = db.execute(
            """
            SELECT current_streak, best_streak
            FROM progress
            WHERE guild_id = ? AND user_id = ? AND language = ?
            """,
            (guild_id, user_id, language)
        ).fetchone()

        current_streak = int(progress["current_streak"])
        best_streak = int(progress["best_streak"])

        if result == "win":
            current_streak += 1
            best_streak = max(best_streak, current_streak)

        elif result == "loss":
            current_streak = 0

        # Update overall progress statistics.
        db.execute(
            """
            UPDATE progress
            SET games_played = games_played + 1,
                wins = wins + ?,
                losses = losses + ?,
                draws = draws + ?,
                current_streak = ?,
                best_streak = ?,
                favorite_game = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ? AND language = ?
            """,
            (
                int(result == "win"),
                int(result == "loss"),
                int(result == "draw"),
                current_streak,
                best_streak,
                game_id,
                guild_id,
                user_id,
                language
            )
        )

        # Apply XP inside this same transaction.
        xp_result = _apply_xp(
            db,
            guild_id,
            user_id,
            language,
            xp_reward
        )

        # Apply coins only when the reward is positive.
        # Zero coins is a valid reward, not an error.
        if coin_reward > 0:

            db.execute(
                """
                UPDATE wallets
                SET coins = coins + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ? AND user_id = ?
                """,
                (coin_reward, guild_id, user_id)
            )

            db.execute(
                """
                INSERT INTO wallet_transactions (
                    guild_id,
                    user_id,
                    transaction_type,
                    amount,
                    description
                )
                VALUES (?, ?, 'earn', ?, ?)
                """,
                (
                    guild_id,
                    user_id,
                    coin_reward,
                    f"Game reward: {game_id}"
                )
            )

        wallet_result = _get_wallet_dict(
            db,
            guild_id,
            user_id
        )

        # Update active season statistics.
        active_season = db.execute(
            """
            SELECT id
            FROM seasons
            WHERE guild_id = ?
                AND language = ?
                AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (guild_id, language)
        ).fetchone()

        if active_season:

            db.execute(
                """
                INSERT INTO season_stats (
                    season_id,
                    user_id,
                    username,
                    xp,
                    wins,
                    losses,
                    draws,
                    games_played
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)

                ON CONFLICT(season_id, user_id)
                DO UPDATE SET
                    username = excluded.username,
                    xp = xp + excluded.xp,
                    wins = wins + excluded.wins,
                    losses = losses + excluded.losses,
                    draws = draws + excluded.draws,
                    games_played = games_played + 1
                """,
                (
                    active_season["id"],
                    user_id,
                    username,
                    xp_reward,
                    int(result == "win"),
                    int(result == "loss"),
                    int(result == "draw")
                )
            )

    return {
        "result": result,
        "xp_reward": xp_reward,
        "coin_reward": coin_reward,
        "xp": xp_result,
        "wallet": wallet_result
    }


def get_game_stats(guild_id, user_id, game_id=None):

    with get_connection() as db:

        if game_id is not None:
            return db.execute(
                """
                SELECT *
                FROM game_stats
                WHERE guild_id = ? AND user_id = ? AND game_id = ?
                """,
                (str(guild_id), str(user_id), str(game_id))
            ).fetchone()

        return db.execute(
            """
            SELECT *
            FROM game_stats
            WHERE guild_id = ? AND user_id = ?
            ORDER BY games_played DESC
            """,
            (str(guild_id), str(user_id))
        ).fetchall()


# ========================================================
# WALLET SYSTEM
# ========================================================

def ensure_wallet(guild_id, user_id):

    with get_connection() as db:
        _ensure_wallet(db, guild_id, user_id)


def get_wallet(guild_id, user_id):

    with get_connection() as db:

        _ensure_wallet(db, guild_id, user_id)

        return db.execute(
            """
            SELECT coins, bank
            FROM wallets
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(guild_id), str(user_id))
        ).fetchone()


def add_coins(guild_id, user_id, amount, description="Reward"):

    amount = int(amount)

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    with get_connection() as db:

        _ensure_wallet(db, guild_id, user_id)

        db.execute(
            """
            UPDATE wallets
            SET coins = coins + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ?
            """,
            (amount, str(guild_id), str(user_id))
        )

        db.execute(
            """
            INSERT INTO wallet_transactions (
                guild_id,
                user_id,
                transaction_type,
                amount,
                description
            )
            VALUES (?, ?, 'earn', ?, ?)
            """,
            (
                str(guild_id),
                str(user_id),
                amount,
                str(description)
            )
        )

        return _get_wallet_dict(
            db,
            guild_id,
            user_id
        )


def remove_coins(guild_id, user_id, amount, description="Purchase"):

    amount = int(amount)

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    with get_connection() as db:

        _ensure_wallet(db, guild_id, user_id)

        cursor = db.execute(
            """
            UPDATE wallets
            SET coins = coins - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ? AND coins >= ?
            """,
            (
                amount,
                str(guild_id),
                str(user_id),
                amount
            )
        )

        if cursor.rowcount != 1:
            return False

        db.execute(
            """
            INSERT INTO wallet_transactions (
                guild_id,
                user_id,
                transaction_type,
                amount,
                description
            )
            VALUES (?, ?, 'spend', ?, ?)
            """,
            (
                str(guild_id),
                str(user_id),
                amount,
                str(description)
            )
        )

        return True


# ========================================================
# BANK SYSTEM
# ========================================================

def deposit_coins(guild_id, user_id, amount):

    amount = int(amount)

    if amount <= 0:
        return False

    with get_connection() as db:

        _ensure_wallet(db, guild_id, user_id)

        cursor = db.execute(
            """
            UPDATE wallets
            SET coins = coins - ?,
                bank = bank + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ? AND coins >= ?
            """,
            (
                amount,
                amount,
                str(guild_id),
                str(user_id),
                amount
            )
        )

        if cursor.rowcount != 1:
            return False

        db.execute(
            """
            INSERT INTO wallet_transactions (
                guild_id,
                user_id,
                transaction_type,
                amount,
                description
            )
            VALUES (?, ?, 'deposit', ?, 'Bank deposit')
            """,
            (str(guild_id), str(user_id), amount)
        )

        return True


def withdraw_coins(guild_id, user_id, amount):

    amount = int(amount)

    if amount <= 0:
        return False

    with get_connection() as db:

        _ensure_wallet(db, guild_id, user_id)

        cursor = db.execute(
            """
            UPDATE wallets
            SET coins = coins + ?,
                bank = bank - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ? AND bank >= ?
            """,
            (
                amount,
                amount,
                str(guild_id),
                str(user_id),
                amount
            )
        )

        if cursor.rowcount != 1:
            return False

        db.execute(
            """
            INSERT INTO wallet_transactions (
                guild_id,
                user_id,
                transaction_type,
                amount,
                description
            )
            VALUES (?, ?, 'withdraw', ?, 'Bank withdrawal')
            """,
            (str(guild_id), str(user_id), amount)
        )

        return True


def get_wallet_history(guild_id, user_id, limit=10):

    limit = max(1, min(int(limit), 50))

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM wallet_transactions
            WHERE guild_id = ? AND user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (str(guild_id), str(user_id), limit)
        ).fetchall()


# ========================================================
# CHARACTER SYSTEM
# ========================================================

def select_character(guild_id, user_id, character_id):

    character_id = str(character_id).strip()

    if not character_id:
        raise ValueError("Character ID cannot be empty.")

    with get_connection() as db:

        _ensure_player(
            db,
            guild_id,
            user_id,
            str(user_id)
        )

        db.execute(
            """
            INSERT INTO selected_characters (
                guild_id,
                user_id,
                character_id
            )
            VALUES (?, ?, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                character_id = excluded.character_id,
                selected_at = CURRENT_TIMESTAMP
            """,
            (
                str(guild_id),
                str(user_id),
                character_id
            )
        )

    return True


def get_selected_character(guild_id, user_id):

    with get_connection() as db:
        return db.execute(
            """
            SELECT character_id, selected_at
            FROM selected_characters
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(guild_id), str(user_id))
        ).fetchone()


# ========================================================
# ACHIEVEMENTS
# ========================================================

def get_achievement_count(guild_id, user_id, language):

    _validate_language(language)

    with get_connection() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM achievements
            WHERE guild_id = ? AND user_id = ? AND language = ?
            """,
            (str(guild_id), str(user_id), language)
        ).fetchone()

        return row["total"] if row else 0


def unlock_achievement(
    guild_id,
    user_id,
    language,
    achievement_key
):

    _validate_language(language)

    achievement_key = str(achievement_key).strip()

    if not achievement_key:
        raise ValueError("Achievement key cannot be empty.")

    with get_connection() as db:

        # Prevent foreign-key errors for unregistered players.
        _ensure_player(
            db,
            guild_id,
            user_id,
            str(user_id)
        )

        _ensure_progress(
            db,
            guild_id,
            user_id,
            language
        )

        cursor = db.execute(
            """
            INSERT OR IGNORE INTO achievements (
                guild_id,
                user_id,
                language,
                achievement_key
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                str(guild_id),
                str(user_id),
                language,
                achievement_key
            )
        )

        return cursor.rowcount == 1


# ========================================================
# PLAYER CARD DATA
# ========================================================

def get_player_card_data(guild_id, user_id, language):

    _validate_language(language)

    with get_connection() as db:
        return db.execute(
            """
            SELECT
                p.username,
                p.active_language,
                pr.level,
                pr.xp,
                pr.lifetime_xp,
                pr.prestige,
                pr.games_played,
                pr.wins,
                pr.losses,
                pr.draws,
                pr.current_streak,
                pr.best_streak,
                pr.favorite_game
            FROM players p
            JOIN progress pr
                ON pr.guild_id = p.guild_id
                AND pr.user_id = p.user_id
            WHERE p.guild_id = ?
                AND p.user_id = ?
                AND pr.language = ?
            """,
            (str(guild_id), str(user_id), language)
        ).fetchone()


# ========================================================
# BOT MESSAGE STORAGE
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
                str(message_key),
                str(channel_id),
                str(message_id)
            )
        )


def get_bot_message(guild_id, message_key):

    with get_connection() as db:
        return db.execute(
            """
            SELECT *
            FROM bot_messages
            WHERE guild_id = ? AND message_key = ?
            """,
            (str(guild_id), str(message_key))
        ).fetchone()


# ========================================================
# SEASONS
# ========================================================

def get_active_season(guild_id, language):

    _validate_language(language)

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
            (str(guild_id), language)
        ).fetchone()


def get_all_time_leaderboard(guild_id, language, limit=10):

    _validate_language(language)

    limit = max(1, min(int(limit), 10))

    with get_connection() as db:
        return db.execute(
            """
            SELECT
                p.user_id,
                p.username,
                pr.level,
                pr.xp,
                pr.lifetime_xp,
                pr.wins,
                pr.games_played
            FROM progress pr
            JOIN players p
                ON p.guild_id = pr.guild_id
                AND p.user_id = pr.user_id
            WHERE pr.guild_id = ? AND pr.language = ?
            ORDER BY
                pr.level DESC,
                pr.xp DESC,
                pr.wins DESC,
                pr.lifetime_xp DESC
            LIMIT ?
            """,
            (str(guild_id), language, limit)
        ).fetchall()


def get_season_leaderboard(guild_id, language, limit=10):

    _validate_language(language)

    limit = max(1, min(int(limit), 10))

    with get_connection() as db:

        season = db.execute(
            """
            SELECT id, name
            FROM seasons
            WHERE guild_id = ?
                AND language = ?
                AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (str(guild_id), language)
        ).fetchone()

        if season is None:
            return None, []

        rows = db.execute(
            """
            SELECT
                user_id,
                username,
                xp,
                wins,
                games_played
            FROM season_stats
            WHERE season_id = ?
            ORDER BY xp DESC, wins DESC, games_played DESC
            LIMIT ?
            """,
            (season["id"], limit)
        ).fetchall()

        return season, rows


# ========================================================
# DATABASE HEALTH CHECK
# ========================================================

def database_health_check():

    try:
        with get_connection() as db:
            result = db.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            return bool(result and result[0] == "ok")

    except sqlite3.Error:
        return False
