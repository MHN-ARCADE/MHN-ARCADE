"""
MHN ARCADE V3 - Coin Flip Tests

Tests for:
- Coin Flip results
- Consecutive flips
- Game history
- State summary
- Invalid player data
"""

import unittest

from engine.games.coin_flip import (
    CoinFlip,
    CoinFlipError,
)


class SequenceRNG:
    """Deterministic RNG for predictable Coin Flip tests."""

    def __init__(self):
        self.results = [
            CoinFlip.SIDES[0],
            CoinFlip.SIDES[1],
        ]

    def choice(self, sides):
        return self.results.pop(0)


class CoinFlipTests(unittest.TestCase):

    def setUp(self):
        self.game = CoinFlip(
            player_id="100",
            player_name="PlayerOne",
            rng=SequenceRNG(),
        )

    def test_first_flip_returns_heads(self):
        result = self.game.flip()

        self.assertEqual(result.side, "heads")
        self.assertEqual(result.side_ar, "الصورة")
        self.assertEqual(result.flip_number, 1)

    def test_second_flip_returns_tails(self):
        self.game.flip()
        result = self.game.flip()

        self.assertEqual(result.side, "tails")
        self.assertEqual(result.side_ar, "الكتابة")
        self.assertEqual(result.flip_number, 2)

    def test_flip_history_is_preserved(self):
        self.game.flip()
        self.game.flip()

        self.assertEqual(self.game.total_flips, 2)
        self.assertEqual(len(self.game.history), 2)
        self.assertEqual(
            self.game.last_result.side,
            "tails",
        )

    def test_game_state_contains_correct_summary(self):
        self.game.flip()

        state = self.game.get_state()

        self.assertEqual(state["game_id"], "coin_flip")
        self.assertEqual(state["player_id"], "100")
        self.assertEqual(state["player_name"], "PlayerOne")
        self.assertEqual(state["total_flips"], 1)
        self.assertEqual(
            state["last_result"]["side"],
            "heads",
        )
        self.assertEqual(len(state["history"]), 1)

    def test_empty_player_id_is_rejected(self):
        with self.assertRaises(CoinFlipError):
            CoinFlip(
                player_id="",
                player_name="PlayerOne",
            )

    def test_empty_player_name_is_rejected(self):
        with self.assertRaises(CoinFlipError):
            CoinFlip(
                player_id="100",
                player_name="",
            )


if __name__ == "__main__":
    unittest.main()
