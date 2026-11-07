"""
MHN ARCADE V3 - Musical Roulette

Core game mechanics for the multiplayer elimination game.

This module is independent from Discord.py.
It manages turns, eliminations, and the final winner.
"""

from __future__ import annotations

import secrets

from dataclasses import dataclass
from typing import Any

from ..core import (
    GameSession,
    PlayerStatus,
    SessionError,
    SessionStatus,
)


# =========================================================
# ERRORS
# =========================================================

class MusicalRouletteError(Exception):
    """Raised when a Musical Roulette action is invalid."""


# =========================================================
# GAME STATE
# =========================================================

@dataclass(frozen=True)
class Elimination:
    """Represents one player's elimination."""

    eliminated_id: str
    eliminated_name: str

    chosen_by_id: str
    chosen_by_name: str

    round_number: int


@dataclass(frozen=True)
class RouletteResult:
    """Represents the completed game result."""

    winner_id: str
    winner_name: str
    total_rounds: int


# =========================================================
# MUSICAL ROULETTE
# =========================================================

class MusicalRoulette:
    """
    Manages Musical Roulette game mechanics.

    Rules:
    - A random active player starts as chooser.
    - The chooser eliminates another active player.
    - A player cannot eliminate themselves.
    - Eliminated players cannot be selected again.
    - The last remaining player wins.
    """

    GAME_ID = "musical_roulette"

    def __init__(
        self,
        session: GameSession,
        rng: Any = None,
    ) -> None:

        if not isinstance(session, GameSession):
            raise MusicalRouletteError(
                "A valid GameSession is required."
            )

        if session.game_id != self.GAME_ID:
            raise MusicalRouletteError(
                "The session is not a Musical Roulette game."
            )

        self.session = session
        self._rng = rng or secrets.SystemRandom()

        self._started = False
        self._finished = False

        self._current_chooser_id: str | None = None
        self._round_number = 0

        self._eliminations: list[Elimination] = []
        self._result: RouletteResult | None = None

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _get_player(self, user_id: str | int):
        player = self.session.get_player(str(user_id))

        if player is None:
            raise MusicalRouletteError(
                "Player is not part of this game."
            )

        return player

    def _get_remaining_players(self):
        return [
            player
            for player in self.session.players.values()
            if player.status == PlayerStatus.ACTIVE
        ]

    def _require_running(self) -> None:

        if not self._started:
            raise MusicalRouletteError(
                "The game has not started."
            )

        if self._finished:
            raise MusicalRouletteError(
                "The game has already finished."
            )

        if self.session.status != SessionStatus.RUNNING:
            raise MusicalRouletteError(
                "The session is not running."
            )

    def _choose_next_player(self) -> str | None:

        remaining = self._get_remaining_players()

        if not remaining:
            return None

        selected = self._rng.choice(remaining)

        return selected.user_id

    def _check_winner(self) -> RouletteResult | None:

        remaining = self._get_remaining_players()

        if len(remaining) != 1:
            return None

        winner = remaining[0]

        winner.status = PlayerStatus.WINNER
        winner.result = "win"

        self._finished = True

        self._result = RouletteResult(
            winner_id=winner.user_id,
            winner_name=winner.username,
            total_rounds=self._round_number,
        )

        self.session.metadata["musical_roulette_result"] = {
            "winner_id": winner.user_id,
            "winner_name": winner.username,
            "total_rounds": self._round_number,
        }

        return self._result

    # =====================================================
    # START GAME
    # =====================================================

    def start(self) -> str:

        if self._started:
            raise MusicalRouletteError(
                "The game has already started."
            )

        if self.session.status != SessionStatus.RUNNING:
            raise MusicalRouletteError(
                "The session must be running before starting "
                "Musical Roulette."
            )

        remaining = self._get_remaining_players()

        if len(remaining) < 3:
            raise MusicalRouletteError(
                "Musical Roulette requires at least "
                "three active players."
            )

        self._started = True
        self._round_number = 1

        self._current_chooser_id = self._choose_next_player()

        if self._current_chooser_id is None:
            raise MusicalRouletteError(
                "Could not select the first player."
            )

        self.session.metadata["musical_roulette"] = {
            "started": True,
            "round": self._round_number,
            "current_chooser_id": self._current_chooser_id,
            "eliminations": [],
        }

        return self._current_chooser_id

    # =====================================================
    # CURRENT TURN
    # =====================================================

    @property
    def current_chooser_id(self) -> str | None:
        return self._current_chooser_id

    @property
    def current_chooser(self):

        if self._current_chooser_id is None:
            return None

        return self.session.get_player(
            self._current_chooser_id
        )

    @property
    def round_number(self) -> int:
        return self._round_number

    @property
    def is_finished(self) -> bool:
        return self._finished

    @property
    def result(self) -> RouletteResult | None:
        return self._result

    @property
    def eliminations(self) -> tuple[Elimination, ...]:
        return tuple(self._eliminations)

    @property
    def remaining_players(self):
        return tuple(self._get_remaining_players())

    # =====================================================
    # AVAILABLE TARGETS
    # =====================================================

    def get_available_targets(self):

        self._require_running()

        if self._current_chooser_id is None:
            raise MusicalRouletteError(
                "There is no active chooser."
            )

        return tuple(
            player
            for player in self._get_remaining_players()
            if player.user_id != self._current_chooser_id
        )

    # =====================================================
    # ELIMINATE PLAYER
    # =====================================================

    def eliminate(
        self,
        chooser_id: str | int,
        target_id: str | int,
    ) -> Elimination:

        self._require_running()

        chooser_id = str(chooser_id)
        target_id = str(target_id)

        if chooser_id != self._current_chooser_id:
            raise MusicalRouletteError(
                "It is not this player's turn."
            )

        if chooser_id == target_id:
            raise MusicalRouletteError(
                "A player cannot eliminate themselves."
            )

        chooser = self._get_player(chooser_id)
        target = self._get_player(target_id)

        if chooser.status != PlayerStatus.ACTIVE:
            raise MusicalRouletteError(
                "The chooser is not an active player."
            )

        if target.status != PlayerStatus.ACTIVE:
            raise MusicalRouletteError(
                "The selected player is not active."
            )

        target.status = PlayerStatus.ELIMINATED
        target.result = "loss"

        elimination = Elimination(
            eliminated_id=target.user_id,
            eliminated_name=target.username,
            chosen_by_id=chooser.user_id,
            chosen_by_name=chooser.username,
            round_number=self._round_number,
        )

        self._eliminations.append(elimination)

        self.session.metadata["musical_roulette"][
            "eliminations"
        ].append({
            "eliminated_id": target.user_id,
            "eliminated_name": target.username,
            "chosen_by_id": chooser.user_id,
            "chosen_by_name": chooser.username,
            "round_number": self._round_number,
        })

        # Check whether only one player remains.
        winner = self._check_winner()

        if winner is not None:
            self._current_chooser_id = None

            self.session.metadata["musical_roulette"][
                "current_chooser_id"
            ] = None

            return elimination

        # Select the next chooser from remaining players.
        self._round_number += 1

        self._current_chooser_id = self._choose_next_player()

        self.session.metadata["musical_roulette"][
            "round"
        ] = self._round_number

        self.session.metadata["musical_roulette"][
            "current_chooser_id"
        ] = self._current_chooser_id

        return elimination

    # =====================================================
    # ABORT GAME
    # =====================================================

    def abort(self) -> None:

        if self._finished:
            raise MusicalRouletteError(
                "The game has already finished."
            )

        self._finished = True
        self._current_chooser_id = None

        self.session.metadata["musical_roulette"][
            "aborted"
        ] = True

    # =====================================================
    # GAME SUMMARY
    # =====================================================

    def get_state(self) -> dict[str, Any]:

        return {
            "game_id": self.GAME_ID,
            "started": self._started,
            "finished": self._finished,
            "round": self._round_number,
            "current_chooser_id": self._current_chooser_id,
            "remaining_players": [
                {
                    "user_id": player.user_id,
                    "username": player.username,
                }
                for player in self._get_remaining_players()
            ],
            "eliminations": [
                {
                    "eliminated_id": item.eliminated_id,
                    "eliminated_name": item.eliminated_name,
                    "chosen_by_id": item.chosen_by_id,
                    "chosen_by_name": item.chosen_by_name,
                    "round_number": item.round_number,
                }
                for item in self._eliminations
            ],
            "winner": (
                {
                    "user_id": self._result.winner_id,
                    "username": self._result.winner_name,
                }
                if self._result is not None
                else None
            ),
        }
