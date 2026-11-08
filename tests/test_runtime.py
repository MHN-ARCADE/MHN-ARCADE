
"""
MHN ARCADE V3 - Runtime Tests

Tests for:
- Runtime component wiring
- Isolated database initialization
- Idempotent initialization
- Runtime readiness checks
- Clean shutdown
- Runtime factory
"""

import tempfile
import unittest

from pathlib import Path

from engine.lobby import LobbyManager
from engine.registry import GameRegistry
from engine.repository import SQLiteSessionRepository
from engine.runner import GameRunner
from engine.runtime import (
    RuntimeError as V3RuntimeError,
    V3Runtime,
    create_v3_runtime,
)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.db_path = (
            Path(self.temp_dir.name)
            / "data"
            / "mhn_arcade_v3.db"
        )

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_runtime_components_are_connected(self):
        runtime = V3Runtime(db_path=self.db_path)

        self.assertIsInstance(
            runtime.repository,
            SQLiteSessionRepository,
        )

        self.assertIsInstance(
            runtime.lobbies,
            LobbyManager,
        )

        self.assertIsInstance(
            runtime.registry,
            GameRegistry,
        )

        self.assertIsInstance(
            runtime.runner,
            GameRunner,
        )

        self.assertIs(
            runtime.lobbies.sessions,
            runtime.sessions,
        )

        self.assertIs(
            runtime.runner.lobbies,
            runtime.lobbies,
        )

        self.assertEqual(
            runtime.registry.game_ids,
            ("coin_flip", "musical_roulette"),
        )

        await runtime.shutdown()

    async def test_initialize_creates_isolated_database(self):
        runtime = V3Runtime(db_path=self.db_path)

        self.assertFalse(self.db_path.exists())

        await runtime.initialize()

        self.assertTrue(self.db_path.exists())
        self.assertTrue(runtime.initialized)

        self.assertEqual(
            runtime.get_status()["database"],
            str(self.db_path),
        )

        await runtime.shutdown()

    async def test_initialize_is_idempotent(self):
        runtime = V3Runtime(db_path=self.db_path)

        first_result = await runtime.initialize()
        second_result = await runtime.initialize()

        self.assertIs(first_result, runtime)
        self.assertIs(second_result, runtime)
        self.assertTrue(runtime.initialized)

        await runtime.shutdown()

    async def test_require_initialized_rejects_unready_runtime(self):
        runtime = V3Runtime(db_path=self.db_path)

        with self.assertRaises(V3RuntimeError):
            runtime.require_initialized()

        await runtime.initialize()

        runtime.require_initialized()

        await runtime.shutdown()

    async def test_shutdown_closes_runtime(self):
        runtime = V3Runtime(db_path=self.db_path)

        await runtime.initialize()
        await runtime.shutdown()

        self.assertFalse(runtime.initialized)
        self.assertTrue(runtime.get_status()["closed"])

        with self.assertRaises(V3RuntimeError):
            runtime.require_initialized()

        await runtime.shutdown()

    async def test_closed_runtime_cannot_be_reinitialized(self):
        runtime = V3Runtime(db_path=self.db_path)

        await runtime.initialize()
        await runtime.shutdown()

        with self.assertRaises(V3RuntimeError):
            await runtime.initialize()

    async def test_create_v3_runtime_returns_ready_runtime(self):
        runtime = await create_v3_runtime(
            db_path=self.db_path
        )

        self.assertIsInstance(runtime, V3Runtime)
        self.assertTrue(runtime.initialized)
        self.assertTrue(self.db_path.exists())

        await runtime.shutdown()


if __name__ == "__main__":
    unittest.main()
