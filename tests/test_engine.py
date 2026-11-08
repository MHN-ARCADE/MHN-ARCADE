
"""
MHN ARCADE V3 - Engine Tests

Tests for:
- Default game catalog
- Single-player preparation
- Multiplayer lobby creation
- Musical Roulette launch
- Winner results
- Group draw results
- Player reconnection
- Disconnect grace expiration
- Voluntary surrender
- Lobby host transfer
"""

import asyncio
import unittest

from engine.catalog import (
    build_default_registry,
    get_catalog_summary,
)
from engine.core import (
    PlayerStatus,
    SessionManager,
    SessionStatus,
)
from engine.games.musical_roulette import MusicalRoulette
from engine.registry import GameMode
from engine.runner import GameRunner


class FirstPlayerRNG:
    """Deterministic RNG for predictable game tests."""

    @staticmethod
    def choice(players):
        return players[0]


class EngineTests(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.sessions = SessionManager(
            disconnect_grace_seconds=60
        )

        self.registry = build_default_registry()

        self.runner = GameRunner(
            registry=self.registry,
        )

        self.runner.lobbies.sessions = self.sessions

    def test_default_catalog(self):
        summary = get_catalog_summary(self.registry)

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["single_player"], 1)
        self.assertEqual(summary["multiplayer"], 1)

        self.assertIsNotNone(
            self.registry.get("musical_roulette")
        )

        self.assertIsNotNone(
            self.registry.get("coin_flip")
        )

    async def test_single_player_preparation(self):
        launch = await self.runner.prepare_single_player_game(
            game_id="coin_flip",
            player_id="100",
            player_name="PlayerOne",
        )

        self.assertEqual(
            launch.definition.game_id,
            "coin_flip",
        )

        self.assertIsNone(launch.session)
        self.assertIsNone(launch.handler)

    async def test_multiplayer_lobby_creation(self):
        session = await self.runner.create_multiplayer_lobby(
            game_id="musical_roulette",
            guild_id="guild-1",
            host_id="100",
            host_name="PlayerOne",
        )

        await self.runner.lobbies.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        await self.runner.lobbies.join(
            session.session_id,
            "300",
            "PlayerThree",
        )

        self.assertEqual(session.player_count, 3)
        self.assertEqual(session.status, SessionStatus.LOBBY)

        self.assertEqual(
            session.metadata["game_mode"],
            GameMode.MULTIPLAYER.value,
        )


    async def test_musical_roulette_launch_and_winner(self):
        session = await self.runner.create_multiplayer_lobby(
            game_id="musical_roulette",
            guild_id="guild-2",
            host_id="100",
            host_name="PlayerOne",
        )

        await self.runner.lobbies.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        await self.runner.lobbies.join(
            session.session_id,
            "300",
            "PlayerThree",
        )

        launch = await self.runner.start_multiplayer_game(
            session_id=session.session_id,
            host_id="100",
        )

        self.assertIsInstance(
            launch.handler,
            MusicalRoulette,
        )

        self.assertEqual(
            session.status,
            SessionStatus.RUNNING,
        )

        game = launch.handler

        first_chooser = game.current_chooser_id

        self.assertIn(
            first_chooser,
            ("100", "200", "300"),
        )

        game._rng = FirstPlayerRNG()

        first_target = game.get_available_targets()[0].user_id

        await game.eliminate(
            first_chooser,
            first_target,
        )

        self.assertEqual(
            session.get_player(first_target).status,
            PlayerStatus.ELIMINATED,
        )

        second_chooser = game.current_chooser_id

        second_target = game.get_available_targets()[0].user_id

        await game.eliminate(
            second_chooser,
            second_target,
        )

        self.assertTrue(game.is_finished)

        self.assertEqual(
            session.status,
            SessionStatus.COMPLETED,
        )

        self.assertFalse(game.result.is_draw)

        winner_id = game.result.winner_id

        self.assertIsNotNone(winner_id)

        self.assertEqual(
            session.get_player(winner_id).result,
            "win",
        )

        for player in session.players.values():
            if player.user_id != winner_id:
                self.assertEqual(player.result, "loss")

    async def test_group_draw_when_no_players_remain(self):
        session = await self.runner.create_multiplayer_lobby(
            game_id="musical_roulette",
            guild_id="guild-3",
            host_id="100",
            host_name="PlayerOne",
        )

        await self.runner.lobbies.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        await self.runner.lobbies.join(
            session.session_id,
            "300",
            "PlayerThree",
        )

        launch = await self.runner.start_multiplayer_game(
            session_id=session.session_id,
            host_id="100",
        )

        game = launch.handler

        for player in session.players.values():
            player.status = PlayerStatus.SURRENDERED

        result = await game.finalize()

        self.assertTrue(game.is_finished)
        self.assertTrue(result.is_draw)
        self.assertIsNone(result.winner_id)

        self.assertEqual(
            session.status,
            SessionStatus.COMPLETED,
        )

        for player in session.players.values():
            self.assertEqual(player.result, "draw")
            self.assertEqual(player.status, PlayerStatus.DRAW)

    async def test_player_can_reconnect(self):
        session = await self.sessions.create_session(
            guild_id="guild-4",
            game_id="musical_roulette",
            host_id="100",
            host_name="PlayerOne",
            min_players=2,
        )

        await self.sessions.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        await self.sessions.start(
            session.session_id,
            "100",
        )

        await self.sessions.mark_disconnected(
            session.session_id,
            "200",
        )

        self.assertEqual(
            session.get_player("200").status,
            PlayerStatus.DISCONNECTED,
        )

        reconnected = await self.sessions.reconnect(
            session.session_id,
            "200",
        )

        self.assertTrue(reconnected)

        self.assertEqual(
            session.get_player("200").status,
            PlayerStatus.ACTIVE,
        )

    async def test_disconnect_grace_expiration(self):
        sessions = SessionManager(
            disconnect_grace_seconds=0.01
        )

        session = await sessions.create_session(
            guild_id="guild-5",
            game_id="musical_roulette",
            host_id="100",
            host_name="PlayerOne",
            min_players=2,
        )

        await sessions.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        await sessions.start(
            session.session_id,
            "100",
        )

        events = []

        sessions.add_session_listener(
            session.session_id,
            lambda current_session, user_id, event:
                events.append((user_id, event)),
        )

        await sessions.mark_disconnected(
            session.session_id,
            "200",
        )

        self.assertEqual(
            session.get_player("200").status,
            PlayerStatus.DISCONNECTED,
        )

        await asyncio.sleep(0.05)

        self.assertEqual(
            session.get_player("200").status,
            PlayerStatus.SURRENDERED,
        )

        self.assertIn(
            ("200", "disconnect_expired"),
            events,
        )

    async def test_voluntary_leave_causes_surrender(self):
        session = await self.sessions.create_session(
            guild_id="guild-6",
            game_id="musical_roulette",
            host_id="100",
            host_name="PlayerOne",
            min_players=2,
        )

        await self.sessions.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        await self.sessions.start(
            session.session_id,
            "100",
        )

        events = []

        self.sessions.add_session_listener(
            session.session_id,
            lambda current_session, user_id, event:
                events.append((user_id, event)),
        )

        await self.sessions.leave(
            session.session_id,
            "200",
        )

        self.assertEqual(
            session.get_player("200").status,
            PlayerStatus.SURRENDERED,
        )

        self.assertIn(
            ("200", "surrendered"),
            events,
        )

    async def test_lobby_host_transfer(self):
        session = await self.sessions.create_session(
            guild_id="guild-7",
            game_id="musical_roulette",
            host_id="100",
            host_name="PlayerOne",
            min_players=2,
        )

        await self.sessions.join(
            session.session_id,
            "200",
            "PlayerTwo",
        )

        await self.sessions.join(
            session.session_id,
            "300",
            "PlayerThree",
        )

        await self.sessions.leave(
            session.session_id,
            "100",
        )

        self.assertEqual(session.host_id, "200")
        self.assertEqual(session.status, SessionStatus.LOBBY)
        self.assertNotIn("100", session.players)


if __name__ == "__main__":
    unittest.main()
