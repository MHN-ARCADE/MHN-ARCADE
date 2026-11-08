
"""
MHN ARCADE V3 - Persistence Integration Tests

Tests for:
- Lobby session persistence
- Session recovery after restart
- Unicode data preservation
- Host transfer persistence
- Running session cleanup after restart
"""

import tempfile
import unittest

from pathlib import Path

from engine.core import (
    PlayerStatus,
    SessionManager,
    SessionStatus,
)
from engine.repository import SQLiteSessionRepository


class PersistenceTests(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.db_path = (
            Path(self.temp_dir.name) / "test_sessions.db"
        )

        self.repository = SQLiteSessionRepository(
            db_path=self.db_path
        )

        self.sessions = SessionManager(
            repository=self.repository
        )

        await self.sessions.initialize()

    async def asyncTearDown(self):
        await self.sessions.shutdown()
        self.temp_dir.cleanup()

    async def test_lobby_session_is_restored_after_restart(self):
        session = await self.sessions.create_session(
            guild_id="guild-1",
            game_id="musical_roulette",
            host_id="100",
            host_name="PlayerOne",
            min_players=2,
            metadata={
                "game_mode": "multiplayer",
                "language": "ar",
            },
        )

        await self.sessions.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        restarted_manager = SessionManager(
            repository=self.repository
        )

        await restarted_manager.initialize()

        restored = await restarted_manager.get_session(
            session.session_id
        )

        self.assertIsNotNone(restored)
        self.assertEqual(restored.status, SessionStatus.LOBBY)
        self.assertEqual(restored.guild_id, "guild-1")
        self.assertEqual(restored.game_id, "musical_roulette")
        self.assertEqual(restored.host_id, "100")
        self.assertEqual(restored.player_count, 2)

        self.assertEqual(
            restored.get_player("200").username,
            "PlayerTwo",
        )

        self.assertEqual(
            restored.metadata["language"],
            "ar",
        )

        await restarted_manager.shutdown()

    async def test_unicode_player_data_is_preserved(self):
        session = await self.sessions.create_session(
            guild_id="guild-2",
            game_id="musical_roulette",
            host_id="300",
            host_name="مهند",
            min_players=1,
        )

        restarted_manager = SessionManager(
            repository=self.repository
        )

        await restarted_manager.initialize()

        restored = await restarted_manager.get_session(
            session.session_id
        )

        self.assertIsNotNone(restored)

        self.assertEqual(
            restored.get_player("300").username,
            "مهند",
        )

        await restarted_manager.shutdown()

    async def test_host_transfer_is_persisted(self):
        session = await self.sessions.create_session(
            guild_id="guild-3",
            game_id="musical_roulette",
            host_id="400",
            host_name="Host",
            min_players=2,
        )

        await self.sessions.join(
            session.session_id,
            "500",
            "PlayerTwo",
        )

        await self.sessions.leave(
            session.session_id,
            "400",
        )

        restarted_manager = SessionManager(
            repository=self.repository
        )

        await restarted_manager.initialize()

        restored = await restarted_manager.get_session(
            session.session_id
        )

        self.assertIsNotNone(restored)
        self.assertEqual(restored.host_id, "500")
        self.assertNotIn("400", restored.players)
        self.assertIn("500", restored.players)

        await restarted_manager.shutdown()

    async def test_running_session_is_not_restored_after_restart(self):
        session = await self.sessions.create_session(
            guild_id="guild-4",
            game_id="musical_roulette",
            host_id="600",
            host_name="Host",
            min_players=2,
        )

        await self.sessions.join(
            session.session_id,
            "700",
            "PlayerTwo",
        )

        await self.sessions.start(
            session.session_id,
            "600",
        )

        self.assertEqual(
            session.status,
            SessionStatus.RUNNING,
        )

        restarted_manager = SessionManager(
            repository=self.repository
        )

        await restarted_manager.initialize()

        restored = await restarted_manager.get_session(
            session.session_id
        )

        self.assertIsNone(restored)

        remaining_records = await self.repository.load_sessions()

        self.assertEqual(remaining_records, [])

        await restarted_manager.shutdown()


if __name__ == "__main__":
    unittest.main()
