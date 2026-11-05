
import sqlite3

DB_NAME = "mhn_arcade.db"


def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                language TEXT DEFAULT NULL,
                level INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                favorite_game TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, achievement_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS special_titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.commit()

    print("MHN ARCADE database initialized successfully!")


def create_player(user_id, username):
    with get_connection() as db:
        db.execute("""
            INSERT OR IGNORE INTO players (user_id, username)
            VALUES (?, ?)
        """, (str(user_id), username))
        db.commit()


def get_player(user_id):
    with get_connection() as db:
        return db.execute("""
            SELECT * FROM players WHERE user_id = ?
        """, (str(user_id),)).fetchone()
