"""
MHN ARCADE V3 — persistent player-profile storage.

This module deliberately keeps the card language separate from
players.active_language. Do NOT call database.select_language() from
the card onboarding flow: switching that field can reset V2 progress.
"""

from database import get_connection

SUPPORTED_PROFILE_LANGUAGES = ("ar", "en")


def initialize_player_profiles():
    """Create the V3 profile table safely; existing V2 data is untouched."""

    with get_connection() as db:

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS player_profiles (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                profile_language TEXT NOT NULL
                    CHECK(profile_language IN ('ar', 'en')),
                character_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        db.execute(
            """
            CREATE INDEX IF NOT EXISTS player_profiles_character_idx
            ON player_profiles(character_id)
            """
        )


def get_player_profile(guild_id, user_id):
    """Return the saved V3 profile row, or None."""

    with get_connection() as db:

        return db.execute(
            """
            SELECT guild_id, user_id, profile_language, character_id,
                   created_at, updated_at
            FROM player_profiles
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(guild_id), str(user_id)),
        ).fetchone()


def save_player_profile(guild_id, user_id, language, character_id):
    """
    Create or update a profile after the user completes onboarding.
    This never changes V2 language/progress or the selected V2 character.
    """

    language = str(language).strip().lower()
    character_id = str(character_id).strip().lower()

    if language not in SUPPORTED_PROFILE_LANGUAGES:
        raise ValueError("Profile language must be 'ar' or 'en'.")

    if not character_id:
        raise ValueError("character_id cannot be empty.")

    with get_connection() as db:

        db.execute(
            """
            INSERT INTO player_profiles (
                guild_id,
                user_id,
                profile_language,
                character_id
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                profile_language = excluded.profile_language,
                character_id = excluded.character_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                str(guild_id),
                str(user_id),
                language,
                character_id
            ),
        )

        return db.execute(
            """
            SELECT guild_id, user_id, profile_language, character_id,
                   created_at, updated_at
            FROM player_profiles
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(guild_id), str(user_id)),
        ).fetchone()


def delete_player_profile(guild_id, user_id):
    """Delete only the V3 profile row; V2 progress is not touched."""

    with get_connection() as db:

        cursor = db.execute(
            """
            DELETE FROM player_profiles
            WHERE guild_id = ? AND user_id = ?
            """,
            (str(guild_id), str(user_id)),
        )

        return cursor.rowcount > 0
