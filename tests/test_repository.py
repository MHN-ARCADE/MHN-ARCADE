
"""
MHN ARCADE V3 - Repository Tests
"""

import tempfile
import unittest

from pathlib import Path

from engine.repository import SQLiteSessionRepository


class RepositoryTests(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.db_path = Path(self.temp_dir.name) / "test.db"

        self.repository = SQLiteSessionRepository(
            db_path=self.db_path,
        )

        await self.repository.initialize()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_initialize_creates_database(self):
        self.assertTrue(self.db_path.exists())

    async def test_save_and_load_session(self):
        session = {
            "session_id": "session-1",
            "guild_id": "guild-1",
            "status": "lobby",
            "game_id": "musical_roulette",
            "players": [
                {
                    "user_id": "100",
                    "username": "PlayerOne",
                },
                {
                    "user_id": "200",
                    "username": "PlayerTwo",
                },
            ],
        }

        await self.repository.save_session(session)

        loaded = await self.repository.load_sessions()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0], session)

    async def test_save_updates_existing_session(self):
        original = {
            "session_id": "session-2",
            "guild_id": "guild-1",
            "status": "lobby",
            "players": [],
        }

        updated = {
            "session_id": "session-2",
            "guild_id": "guild-1",
            "status": "running",
            "players": [
                {
                    "user_id": "100",
                    "username": "PlayerOne",
                },
            ],
        }

        await self.repository.save_session(original)
        await self.repository.save_session(updated)

        loaded = await self.repository.load_sessions()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0], updated)

    async def test_delete_session(self):
        session = {
            "session_id": "session-3",
            "guild_id": "guild-1",
            "status": "lobby",
            "players": [],
        }

        await self.repository.save_session(session)
        await self.repository.delete_session("session-3")

        loaded = await self.repository.load_sessions()

        self.assertEqual(loaded, [])

    async def test_unicode_data_is_preserved(self):
        session = {
            "session_id": "session-4",
            "guild_id": "guild-1",
            "status": "lobby",
            "players": [
                {
                    "user_id": "100",
                    "username": "مهند",
                },
            ],
        }

        await self.repository.save_session(session)

        loaded = await self.repository.load_sessions()

        self.assertEqual(
            loaded[0]["players"][0]["username"],
            "مهند",
        )


if __name__ == "__main__":
    unittest.main()
