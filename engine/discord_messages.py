
"""
MHN ARCADE V3 - Discord Message Lifecycle

Centralized Discord message tracking and cleanup for V3 games.

Responsibilities:
- Bind Discord messages to game sessions.
- Handle cancelled sessions.
- Schedule finished game messages for deletion.
- Keep persistent menus outside this lifecycle.
- Provide reusable methods for future games.
"""

from __future__ import annotations

import logging
from typing import Any

import discord


logger = logging.getLogger("mhn.arcade.v3.discord_messages")


class DiscordMessageLifecycle:
    """
    Central manager for V3 game messages.

    A game can bind its public Discord message to a session.
    When the game finishes, its final UI must be displayed first,
    then finish_session() schedules the message for deletion.
    """

    def __init__(self, cleanup_manager=None) -> None:

        self.cleanup_manager = cleanup_manager

        self._session_messages: dict[
            str,
            discord.Message,
        ] = {}

        self._finished_sessions: set[str] = set()

    # -----------------------------------------------------
    # MESSAGE BINDING
    # -----------------------------------------------------

    def bind_session_message(
        self,
        session_id: str,
        message: discord.Message | None,
    ) -> None:
        """Bind a public Discord message to a game session."""

        if not session_id or message is None:
            return

        if not isinstance(message, discord.Message):
            logger.warning(
                "Cannot bind a non-Discord message to session %s.",
                session_id,
            )
            return

        self._session_messages[str(session_id)] = message

        self._finished_sessions.discard(str(session_id))

        logger.debug(
            "Bound Discord message %s to session %s.",
            message.id,
            session_id,
        )

    def get_session_message(
        self,
        session_id: str,
    ) -> discord.Message | None:
        """Return the Discord message bound to a session."""

        return self._session_messages.get(str(session_id))

    # -----------------------------------------------------
    # FINISHED GAME CLEANUP
    # -----------------------------------------------------

    def finish_session(
        self,
        session_id: str,
        message: discord.Message | None = None,
    ) -> None:
        """
        Schedule a finished session message for deletion.

        Call this only AFTER the final result or terminal state
        has successfully been displayed in Discord.
        """

        session_id = str(session_id)

        if session_id in self._finished_sessions:
            return

        target = (
            message
            or self._session_messages.get(session_id)
        )

        if target is None:
            return

        self._schedule_message(target)

        self._finished_sessions.add(session_id)

        self._session_messages.pop(
            session_id,
            None,
        )

    def finish_message(
        self,
        message: discord.Message | None,
    ) -> None:
        """
        Schedule a standalone finished game message.

        Use this for single-player games that do not have
        a multiplayer session.
        """

        if message is None:
            return

        self._schedule_message(message)

    def _schedule_message(
        self,
        message: discord.Message,
    ) -> None:

        if self.cleanup_manager is None:
            logger.warning(
                "Game cleanup manager is unavailable."
            )
            return

        try:

            self.cleanup_manager.schedule_game_message(
                message
            )

        except Exception:

            logger.exception(
                "Could not schedule game message %s for deletion.",
                getattr(message, "id", "unknown"),
            )

    # -----------------------------------------------------
    # SESSION LIFECYCLE CALLBACK
    # -----------------------------------------------------

    async def on_session_lifecycle(
        self,
        session: Any,
        event: str,
    ) -> None:
        """
        Receive lifecycle events from V3Runtime.

        Completed sessions are finalized by their game UI,
        after the result has been displayed.

        Cancelled sessions are handled here because cancellation
        can also happen outside a Discord button interaction.
        """

        session_id = str(
            getattr(session, "session_id", "")
        )

        if not session_id:
            return

        if event == "completed":
            return

        if event != "cancelled":
            return

        if session_id in self._finished_sessions:
            return

        message = self._session_messages.get(session_id)

        if message is None:
            return

        try:

            await message.edit(
                content="⛔ This game session has ended.",
                embed=None,
                view=None,
            )

            self.finish_session(
                session_id,
                message,
            )

        except discord.NotFound:

            self._session_messages.pop(
                session_id,
                None,
            )

        except discord.HTTPException:

            logger.exception(
                "Could not finalize cancelled session %s.",
                session_id,
            )

    # -----------------------------------------------------
    # SHUTDOWN
    # -----------------------------------------------------

    def clear(self) -> None:
        """Clear in-memory message references."""

        self._session_messages.clear()
        self._finished_sessions.clear()
