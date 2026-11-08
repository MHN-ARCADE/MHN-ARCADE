"""
MHN ARCADE V3 - Coin Flip

Core mechanics for the single-player Coin Flip game.

This module is independent from Discord.py.
"""

from __future__ import annotations

import secrets

from dataclasses import dataclass
from typing import Any, Mapping


# =========================================================
# ERRORS
# =========================================================

class CoinFlipError(Exception):
    """Raised when a Coin Flip action is invalid."""


# =========================================================
# RESULT
# =========================================================

@dataclass(frozen=True)
class CoinFlipResult:
    """Represents one completed coin flip."""

    player_id: str
    player_name: str
    side: str
    side_ar: str
    flip_number: int


# =========================================================
# COIN FLIP
# =========================================================

class CoinFlip:
    """
    Manages Coin Flip game mechanics.

    Rules:
    - A player flips a virtual coin.
    - The result is either heads or tails.
    - Each flip is recorded in the game history.
    - Randomness uses a secure system random generator.
    """

    GAME_ID = "coin_flip"

    SIDES = (
        ("heads", "الصورة"),
        ("tails", "الكتابة"),
    )

    def __init__(
        self,
        *,
        player_id: str,
        player_name: str,
        metadata: Mapping[str, Any] | None = None,
        definition: Any = None,
        rng: Any = None,
    ) -> None:

        if not isinstance(player_id, str) or not player_id.strip():
            raise CoinFlipError(
                "A valid player ID is required."
            )

        if not isinstance(player_name, str) or not player_name.strip():
            raise CoinFlipError(
                "A valid player name is required."
            )

        if definition is not None:
            if getattr(definition, "game_id", None) != self.GAME_ID:
                raise CoinFlipError(
                    "The game definition is not Coin Flip."
                )

        self.player_id = player_id.strip()
        self.player_name = player_name.strip()
        self.metadata = dict(metadata or {})

        self._rng = rng or secrets.SystemRandom()
        self._history: list[CoinFlipResult] = []

    # =====================================================
    # FLIP COIN
    # =====================================================

    def flip(self) -> CoinFlipResult:
        """
        Flip the coin and return the result.
        """

        try:
            side, side_ar = self._rng.choice(self.SIDES)

        except Exception as exc:
            raise CoinFlipError(
                f"Could not flip the coin: {exc}"
            ) from exc

        result = CoinFlipResult(
            player_id=self.player_id,
            player_name=self.player_name,
            side=side,
            side_ar=side_ar,
            flip_number=len(self._history) + 1,
        )

        self._history.append(result)

        return result

    # =====================================================
    # GAME HISTORY
    # =====================================================

    @property
    def history(self) -> tuple[CoinFlipResult, ...]:
        return tuple(self._history)

    @property
    def total_flips(self) -> int:
        return len(self._history)

    @property
    def last_result(self) -> CoinFlipResult | None:
        if not self._history:
            return None

        return self._history[-1]

    # =====================================================
    # GAME SUMMARY
    # =====================================================

    def get_state(self) -> dict[str, Any]:
        return {
            "game_id": self.GAME_ID,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "total_flips": self.total_flips,
            "last_result": (
                {
                    "side": self.last_result.side,
                    "side_ar": self.last_result.side_ar,
                    "flip_number": self.last_result.flip_number,
                }
                if self.last_result is not None
                else None
            ),
            "history": [
                {
                    "side": result.side,
                    "side_ar": result.side_ar,
                    "flip_number": result.flip_number,
                }
                                for result in self._history
            ],
        }
