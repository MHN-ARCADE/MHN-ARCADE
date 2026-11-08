
"""
MHN ARCADE V3 - Musical Roulette

Core game mechanics for the multiplayer elimination game.

This module is independent from Discord.py.
It manages turns, eliminations, disconnects, reconnects,
and final session results.
"""

from __future__ import annotations

import secrets

from dataclasses import dataclass
from typing import Any

from ..core import (
    GameSession,
    PlayerStatus,
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
    - Disconnected players remain in the match during grace time.
    - Disconnected players cannot take turns or be selected.
    - The last remaining eligible player wins.
    - Voluntary leaving means immediate surrender.
    - Disconnecting grants the configured reconnect grace period.
    - Final results are recorded by SessionManager.
    """

    GAME_ID = "musical_roulette"

    def __init__(
        self,
        session: GameSession,
        session_manager: Any,
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

        if session_manager is None:
            raise MusicalRouletteError(
                "A valid SessionManager is required."
            )

        self.session = session
        self.session_manager = session_manager
        self._rng = rng or secrets.SystemRandom()

        self._started = False
        self._finished = False
        self._aborted = False

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
            if player.status in (
                PlayerStatus.ACTIVE,
                PlayerStatus.DISCONNECTED,
            )
        ]

    def _get_active_players(self):

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

    def _update_metadata(self) -> None:

        game_metadata = self.session.metadata.setdefault(
            "musical_roulette",
            {},
        )

        game_metadata["started"] = self._started
        game_metadata["finished"] = self._finished
        game_metadata["aborted"] = self._aborted
        game_metadata["round"] = self._round_number
        game_metadata["current_chooser_id"] = (
            self._current_chooser_id
        )

    def _choose_next_player(self) -> str | None:

        active = self._get_active_players()

        if not active:
            return None

        selected = self._rng.choice(active)

        return selected.user_id

    def _set_next_chooser(self) -> None:

        self._current_chooser_id = self._choose_next_player()
        self._update_metadata()

    def _unregister_listener(self) -> None:

        self.session_manager.remove_session_listener(
            self.session.session_id,
            self._on_session_event,
        )

    # =====================================================
    # SESSION EVENTS
    # =====================================================

    async def _on_session_event(
        self,
        session: GameSession,
        user_id: str,
        event: str,
    ) -> None:
        """
        React to player lifecycle changes from SessionManager.

        Events:
            disconnected
            reconnected
            surrendered
            disconnect_expired
        """

        if self._finished or not self._started:
            return

        if session.session_id != self.session.session_id:
            return

        if session.status != SessionStatus.RUNNING:
            return

        player = self.session.get_player(user_id)

        if player is None:
            return

        if event == "disconnected":

            # A disconnected chooser cannot continue their turn.
            # Keep them in the match during the grace period.
            if self._current_chooser_id == user_id:
                self._set_next_chooser()

            return

        if event == "reconnected":

            # If nobody can currently take a turn, allow the
            # returning player to become the next chooser.
            if self._current_chooser_id is None:
                self._set_next_chooser()

            return

        if event in ("surrendered", "disconnect_expired"):

            # If the player who surrendered held the turn,
            # transfer the turn to another active player.
            if self._current_chooser_id == user_id:
                self._set_next_chooser()

            # Disconnected players still count as remaining.
            # A winner is declared only when one eligible
            # remaining player is left.
            winner = await self._check_winner()

            if winner is not None:
                return

            # If no chooser exists, try again after the
            # remaining player state has been updated.
            if self._current_chooser_id is None:
                self._set_next_chooser()

    # =====================================================
    # COMPLETE GAME
    # =====================================================

    async def _complete_game(
        self,
        winner,
    ) -> RouletteResult:

        if self._finished:
            if self._result is not None:
                return self._result

            raise MusicalRouletteError(
                "The game has already finished."
            )

        if winner.status != PlayerStatus.ACTIVE:
            raise MusicalRouletteError(
                "The winner must be an active player."
            )

        results = {
            player.user_id: (
                "win"
                if player.user_id == winner.user_id
                else "loss"
            )
            for player in self.session.players.values()
        }

        try:
            await self.session_manager.finish(
                session_id=self.session.session_id,
                results=results,
                winner_id=winner.user_id,
            )

        except Exception as exc:
            raise MusicalRouletteError(
                f"Could not save final game results: {exc}"
            ) from exc

        self._result = RouletteResult(
            winner_id=winner.user_id,
            winner_name=winner.username,
            total_rounds=self._round_number,
        )

        self._finished = True
        self._current_chooser_id = None

        self.session.metadata["musical_roulette_result"] = {
            "winner_id": winner.user_id,
            "winner_name": winner.username,
            "total_rounds": self._round_number,
        }

        self._update_metadata()

        self.session.metadata["musical_roulette"][
            "finished"
        ] = True

        self._unregister_listener()

        return self._result

    async def _check_winner(self) -> RouletteResult | None:

        remaining = self._get_remaining_players()

        if len(remaining) != 1:
            return None

        winner = remaining[0]

        # The last remaining player may still be disconnected.
        # Wait for reconnect or expiry instead of declaring
        # a winner during the grace period.
        if winner.status != PlayerStatus.ACTIVE:
            return None

        return await self._complete_game(winner)

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

        active = self._get_active_players()

        if len(active) < 3:
            raise MusicalRouletteError(
                "Musical Roulette requires at least "
                "three active players."
            )

        self._started = True
        self._round_number = 1

        self._current_chooser_id = self._choose_next_player()

        if self._current_chooser_id is None:
            self._started = False

            raise MusicalRouletteError(
                "Could not select the first player."
            )

        try:
            self.session_manager.add_session_listener(
                self.session.session_id,
                self._on_session_event,
            )

        except Exception as exc:
            self._started = False
            self._current_chooser_id = None

            raise MusicalRouletteError(
                f"Could not register session listener: {exc}"
            ) from exc

        self.session.metadata["musical_roulette"] = {
            "started": True,
            "finished": False,
            "aborted": False,
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

        chooser = self._get_player(
            self._current_chooser_id
        )

        if chooser.status != PlayerStatus.ACTIVE:
            raise MusicalRouletteError(
                "The current chooser is not active."
            )

        return tuple(
            player
            for player in self._get_active_players()
            if player.user_id != self._current_chooser_id
        )

    # =====================================================
    # ELIMINATE PLAYER
    # =====================================================

    async def eliminate(
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

        winner = await self._check_winner()

        if winner is not None:
            return elimination

        self._round_number += 1

        self._set_next_chooser()

        return elimination

    # =====================================================
    # RETRY FINALIZATION
    # =====================================================

    async def finalize(self) -> RouletteResult | None:
        """
        Retry finalization if saving results previously failed.
        """

        if self._finished:
            return self._result

        if not self._started:
            raise MusicalRouletteError(
                "The game has not started."
            )

        if self.session.status != SessionStatus.RUNNING:
            raise MusicalRouletteError(
                "The session is not running."
            )

        remaining = self._get_remaining_players()

        if len(remaining) != 1:
            return None

        if remaining[0].status != PlayerStatus.ACTIVE:
            return None

        return await self._complete_game(remaining[0])

    # =====================================================
    # ABORT GAME
    # =====================================================

    async def abort(
        self,
        reason: str = "Game aborted.",
    ) -> None:

        if self._finished:
            raise MusicalRouletteError(
                "The game has already finished."
            )

        if self.session.status != SessionStatus.RUNNING:
            raise MusicalRouletteError(
                "The session is not running."
            )

        try:
            await self.session_manager.cancel_running(
                session_id=self.session.session_id,
                reason=reason,
            )

        except Exception as exc:
            raise MusicalRouletteError(
                f"Could not cancel the game session: {exc}"
            ) from exc

        self._finished = True
        self._aborted = True
        self._current_chooser_id = None

        game_metadata = self.session.metadata.setdefault(
            "musical_roulette",
            {},
        )

        game_metadata["aborted"] = True
        game_metadata["finished"] = True
        game_metadata["current_chooser_id"] = None
        game_metadata["abort_reason"] = reason

        self._unregister_listener()

    # =====================================================
    # GAME SUMMARY
    # =====================================================

    def get_state(self) -> dict[str, Any]:

        return {
            "game_id": self.GAME_ID,
            "started": self._started,
            "finished": self._finished,
            "aborted": self._aborted,
            "session_status": self.session.status.value,
            "round": self._round_number,
            "current_chooser_id": self._current_chooser_id,

            "remaining_players": [
                {
                    "user_id": player.user_id,
                    "username": player.username,
                    "status": player.status.value,
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
