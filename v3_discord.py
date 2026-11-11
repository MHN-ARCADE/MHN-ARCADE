
"""
MHN ARCADE V3 - Discord Integration

Interactive Discord interfaces for the V3 game engine.
Arabic and English interfaces are resolved independently.
The V2 systems remain separate and unchanged.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from engine.runtime import V3Runtime
from engine.i18n import resolve_language, t
from engine.discord_messages import DiscordMessageLifecycle


logger = logging.getLogger("mhn.arcade.v3.discord")

ACHIEVEMENTS_CHANNEL_ID = 1567722630969303090
PURPLE = 0x7C3AED
GAMES_PER_PAGE = 4
DESCRIPTION_LIMIT = 550


# =========================================================
# MESSAGE CLEANUP INTEGRATION
# =========================================================

def schedule_finished_game_message(
    lifecycle: DiscordMessageLifecycle | None,
    message: discord.Message | None,
    session_id: str | None = None,
) -> None:
    """
    Schedule a finished game message through the shared lifecycle manager.

    The final Discord message must be displayed before calling this function.
    """

    if lifecycle is None or message is None:
        return

    try:

        if session_id is not None:
            lifecycle.finish_session(
                session_id=session_id,
                message=message,
            )
        else:
            lifecycle.finish_message(message)

    except Exception:
        logger.exception(
            "Could not schedule finished game message for deletion."
        )


# =========================================================
# HELPERS
# =========================================================

def safe_text(value: str, limit: int) -> str:
    value = str(value or "").strip()

    if len(value) <= limit:
        return value

    return value[:limit - 3] + "..."


async def send_error(
    interaction: discord.Interaction,
    message: str,
) -> None:

    if interaction.response.is_done():
        await interaction.followup.send(
            message,
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            message,
            ephemeral=True,
        )


# =========================================================
# CATALOG EMBEDS
# =========================================================

def build_catalog_pages(
    games: tuple,
    language: str = "en",
) -> list[discord.Embed]:

    if not games:
        embed = discord.Embed(
            title=t("catalog_title", language),
            description=t("catalog_empty", language),
            color=PURPLE,
        )
        embed.set_footer(text="MHN ARCADE V3")
        return [embed]

    pages = []

    total_pages = (
        len(games) + GAMES_PER_PAGE - 1
    ) // GAMES_PER_PAGE

    for page_index in range(0, len(games), GAMES_PER_PAGE):

        page_games = games[
            page_index:page_index + GAMES_PER_PAGE
        ]

        page_number = page_index // GAMES_PER_PAGE + 1

        embed = discord.Embed(
            title=t("catalog_title", language),
            description=t("catalog_description", language),
            color=PURPLE,
        )

        for game in page_games:

            mode_value = game.mode.value

            if language == "ar":
                mode = {
                    "single_player": "لاعب واحد",
                    "multiplayer": "متعدد اللاعبين",
                }.get(
                    mode_value,
                    mode_value.replace("_", " "),
                )
            else:
                mode = mode_value.replace("_", " ").title()

            game_name = (
                game.name_ar
                if language == "ar"
                else game.name_en
            )

            description = (
                game.description_ar
                if language == "ar"
                else game.description_en
            )

            field_value = (
                f"**{t('game_id', language)}:** "
                f"`{game.game_id}`\n"
                f"**{t('game_mode', language)}:** {mode}\n"
                f"**{t('players', language)}:** "
                f"{game.min_players}-{game.max_players}\n"
                f"{safe_text(description, DESCRIPTION_LIMIT)}"
            )

            embed.add_field(
                name=f"🎮 {safe_text(game_name, 250)}",
                value=safe_text(field_value, 1024),
                inline=False,
            )

        if language == "ar":
            footer = (
                f"MHN ARCADE V3 • الصفحة "
                f"{page_number}/{total_pages}"
            )
        else:
            footer = (
                f"MHN ARCADE V3 • Page "
                f"{page_number}/{total_pages}"
            )

        embed.set_footer(text=footer)
        pages.append(embed)

    return pages


# =========================================================
# COIN FLIP EMBED
# =========================================================

def build_coin_flip_embed(
    result=None,
    total_flips: int = 0,
    language: str = "en",
) -> discord.Embed:

    embed = discord.Embed(
        title=t("coin_flip_title", language),
        description=t("coin_flip_description", language),
        color=PURPLE,
    )

    if result is None:

        embed.add_field(
            name=f"🎯 {t('coin_flip_result', language)}",
            value=t("coin_flip_waiting", language),
            inline=False,
        )

    else:

        emoji = (
            "🌕"
            if result.side == "heads"
            else "🌑"
        )

        side_key = (
            "coin_flip_heads"
            if result.side == "heads"
            else "coin_flip_tails"
        )

        side_name = t(side_key, language)

        embed.add_field(
            name=f"{emoji} {t('coin_flip_result', language)}",
            value=f"**{side_name}**",
            inline=False,
        )

        embed.add_field(
            name=t("coin_flip_number", language),
            value=str(result.flip_number),
            inline=True,
        )

    embed.add_field(
        name=t("coin_flip_total", language),
        value=str(total_flips),
        inline=True,
    )

    embed.set_footer(
        text="MHN ARCADE V3 • Coin Flip"
    )

    return embed


# =========================================================
# MUSICAL ROULETTE EMBEDS
# =========================================================

def build_roulette_lobby_embed(
    session,
    language: str = "en",
) -> discord.Embed:

    players = list(session.players.values())
    player_lines = []

    for player in players:

        marker = (
            "👑"
            if str(player.user_id) == str(session.host_id)
            else "🎮"
        )

        player_lines.append(
            f"{marker} **{safe_text(player.username, 60)}**"
        )

    embed = discord.Embed(
        title=t("roulette_title", language),
        description=t("roulette_description", language),
        color=PURPLE,
    )

    embed.add_field(
        name=(
            f"👥 {t('players', language)} "
            f"({session.player_count}/{session.max_players})"
        ),
        value=(
            "\n".join(player_lines)
            if player_lines
            else t("roulette_no_players", language)
        ),
        inline=False,
    )

    embed.add_field(
        name=f"🎯 {t('roulette_requirements', language)}",
        value=(
            f"{t('roulette_minimum', language)}: "
            f"**{session.min_players}**"
        ),
        inline=True,
    )

    embed.add_field(
        name=f"👑 {t('roulette_host', language)}",
        value=f"<@{session.host_id}>",
        inline=True,
    )

    embed.set_footer(
        text=f"Lobby ID: {session.session_id} • MHN ARCADE V3"
    )

    return embed


def build_roulette_game_embed(
    handler,
    language: str = "en",
) -> discord.Embed:

    state = handler.get_state()

    embed = discord.Embed(
        title=t("roulette_title", language),
        color=PURPLE,
    )

    if state["finished"]:

        winner = state.get("winner")

        if state.get("is_draw"):
            embed.description = t(
                "roulette_draw",
                language,
            )

        elif winner:
            embed.description = (
                f"🏆 **{t('roulette_winner', language)}:** "
                f"<@{winner['user_id']}>\n"
                f"{t('roulette_congratulations', language)}"
            )

        else:
            embed.description = t(
                "roulette_ended",
                language,
            )

    else:

        chooser_id = state.get("current_chooser_id")

        embed.description = (
            f"🎯 **{t('roulette_round', language)}:** "
            f"{state['round']}\n"
            f"🗣️ **{t('roulette_current_chooser', language)}:** "
            f"<@{chooser_id}>\n\n"
            f"{t('roulette_choose_player', language)}"
        )

    remaining = state.get(
        "remaining_players",
        [],
    )

    remaining_text = "\n".join(
        f"🟢 <@{player['user_id']}>"
        for player in remaining
    )

    embed.add_field(
        name=(
            f"👥 {t('roulette_remaining', language)} "
            f"({len(remaining)})"
        ),
        value=(
            remaining_text
            or t("roulette_no_players", language)
        ),
        inline=False,
    )

    eliminations = state.get(
        "eliminations",
        [],
    )

    if eliminations:

        recent = eliminations[-8:]

        history = "\n".join(
            f"❌ <@{item['eliminated_id']}> — "
            f"<@{item['chosen_by_id']}>"
            for item in recent
        )

        embed.add_field(
            name=f"📜 {t('roulette_history', language)}",
            value=history,
            inline=False,
        )

    embed.set_footer(
        text="MHN ARCADE V3 • Musical Roulette"
    )

    return embed


# =========================================================
# CATALOG VIEW
# =========================================================

class CatalogView(discord.ui.View):

    def __init__(
        self,
        pages: list[discord.Embed],
        owner_id: int | None,
        language: str = "en",
    ) -> None:

        super().__init__(timeout=180)

        self.pages = pages
        self.owner_id = owner_id
        self.language = language
        self.current_page = 0
        self.message = None

        self.previous_button.label = t(
            "previous",
            language,
        )

        self.next_button.label = t(
            "next",
            language,
        )

        self.update_buttons()

    def update_buttons(self) -> None:

        self.previous_button.disabled = (
            self.current_page <= 0
        )

        self.next_button.disabled = (
            self.current_page >= len(self.pages) - 1
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if (
            self.owner_id is not None
            and interaction.user.id != self.owner_id
        ):

            await interaction.response.send_message(
                t("owner_only", self.language),
                ephemeral=True,
            )

            return False

        return True

    @discord.ui.button(
        label="Previous",
        emoji="⬅️",
        style=discord.ButtonStyle.secondary,
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        self.current_page = max(
            0,
            self.current_page - 1,
        )

        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.pages[self.current_page],
            view=self,
        )

    @discord.ui.button(
        label="Next",
        emoji="➡️",
        style=discord.ButtonStyle.primary,
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        self.current_page = min(
            len(self.pages) - 1,
            self.current_page + 1,
        )

        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.pages[self.current_page],
            view=self,
        )

    async def on_timeout(self) -> None:

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


# =========================================================
# COIN FLIP VIEW
# =========================================================

class CoinFlipView(discord.ui.View):

    def __init__(
        self,
        handler,
        owner_id: int,
        language: str = "en",
        cleanup_manager=None,
    ) -> None:

        super().__init__(timeout=300)

        self.handler = handler
        self.owner_id = owner_id
        self.language = language
        self.cleanup_manager = cleanup_manager

        self.message = None
        self.finished = False

        self.flip_button.label = t(
            "coin_flip_button",
            language,
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await interaction.response.send_message(
                t("owner_only", self.language),
                ephemeral=True,
            )

            return False

        return True

    @discord.ui.button(
        label="Flip Coin",
        emoji="🪙",
        style=discord.ButtonStyle.primary,
    )
    async def flip_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if self.finished:

            await interaction.response.send_message(
                t("coin_flip_finished", self.language),
                ephemeral=True,
            )

            return

        try:

            result = self.handler.flip()

            embed = build_coin_flip_embed(
                result=result,
                total_flips=self.handler.total_flips,
                language=self.language,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=self,
            )

        except Exception:

            logger.exception(
                "Coin Flip action failed."
            )

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    async def on_timeout(self) -> None:

        if self.finished:
            return

        self.finished = True

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is not None:

            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

            schedule_finished_game_message(
                self.cleanup_manager,
                self.message,
            )


# =========================================================
# ROULETTE CAPACITY MODAL
# =========================================================

class RouletteCapacityModal(discord.ui.Modal):
    """Allows the lobby host to change the player capacity."""

    def __init__(
        self,
        lobby_view,
        current_capacity: int,
    ):

        super().__init__(
            title="Change Lobby Capacity"
        )

        self.lobby_view = lobby_view

        self.capacity = discord.ui.TextInput(
            label="Maximum players (3–30)",
            placeholder="Enter a number from 3 to 30",
            default=str(current_capacity),
            min_length=1,
            max_length=2,
            required=True,
        )

        self.add_item(self.capacity)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):

        try:

            session = await self.lobby_view.runtime.runner.lobbies.get(
                self.lobby_view.session_id
            )

            if session is None:

                await send_error(
                    interaction,
                    t(
                        "roulette_unavailable",
                        self.lobby_view.language,
                    ),
                )

                return

            if str(interaction.user.id) != str(session.host_id):

                await send_error(
                    interaction,
                    t(
                        "roulette_host_only",
                        self.lobby_view.language,
                    ),
                )

                return

            try:
                capacity = int(
                    self.capacity.value.strip()
                )
            except ValueError:

                await send_error(
                    interaction,
                    "Please enter a valid number.",
                )

                return

            if not 3 <= capacity <= 30:

                await send_error(
                    interaction,
                    "Capacity must be between 3 and 30 players.",
                )

                return

            if capacity < session.player_count:

                await send_error(
                    interaction,
                    (
                        f"There are already "
                        f"{session.player_count} players in this lobby."
                    ),
                )

                return

            await self.lobby_view.runtime.runner.lobbies.set_capacity(
                session_id=self.lobby_view.session_id,
                host_id=interaction.user.id,
                max_players=capacity,
            )

            await self.lobby_view.refresh_public_message()

            await interaction.response.send_message(
                (
                    f"✅ Lobby capacity updated to "
                    f"**{capacity} players**."
                ),
                ephemeral=True,
            )

        except Exception:

            logger.exception(
                "Lobby capacity update failed."
            )

            await send_error(
                interaction,
                t(
                    "generic_error",
                    self.lobby_view.language,
                ),
            )


# =========================================================
# ROULETTE KICK VIEW
# =========================================================

class RouletteKickView(discord.ui.View):
    """Player selection for the lobby host."""

    def __init__(
        self,
        lobby_view,
        session,
    ):

        super().__init__(timeout=120)

        self.lobby_view = lobby_view
        self.session_id = lobby_view.session_id
        self.host_id = str(session.host_id)

        self.page = 0

        self.players = [
            player
            for player in session.players.values()
            if str(player.user_id) != self.host_id
        ]

        self.page_size = 25

        self.build_select()

    def build_select(self):

        self.clear_items()

        start = self.page * self.page_size
        end = start + self.page_size

        page_players = self.players[start:end]

        if page_players:

            options = [
                discord.SelectOption(
                    label=str(player.username)[:100],
                    value=str(player.user_id),
                    description=(
                        f"Player ID: {player.user_id}"
                    )[:100],
                    emoji="🎮",
                )
                for player in page_players
            ]

            select = discord.ui.Select(
                placeholder="Choose a player to remove",
                min_values=1,
                max_values=1,
                options=options,
            )

            select.callback = self.select_player
            self.add_item(select)

        if self.page > 0:

            previous = discord.ui.Button(
                label="Previous",
                emoji="⬅️",
                style=discord.ButtonStyle.secondary,
            )

            previous.callback = self.previous_page
            self.add_item(previous)

        if end < len(self.players):

            next_button = discord.ui.Button(
                label="Next",
                emoji="➡️",
                style=discord.ButtonStyle.secondary,
            )

            next_button.callback = self.next_page
            self.add_item(next_button)

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if str(interaction.user.id) != self.host_id:

            await interaction.response.send_message(
                t(
                    "roulette_host_only",
                    self.lobby_view.language,
                ),
                ephemeral=True,
            )

            return False

        return True

    async def select_player(
        self,
        interaction: discord.Interaction,
    ):

        try:

            target_id = interaction.data["values"][0]

            session = await self.lobby_view.runtime.runner.lobbies.get(
                self.session_id
            )

            if session is None:

                await interaction.response.send_message(
                    t(
                        "roulette_unavailable",
                        self.lobby_view.language,
                    ),
                    ephemeral=True,
                )

                return

            if str(interaction.user.id) != str(session.host_id):

                await interaction.response.send_message(
                    t(
                        "roulette_host_only",
                        self.lobby_view.language,
                    ),
                    ephemeral=True,
                )

                return

            target = session.get_player(target_id)

            if target is None:

                await interaction.response.send_message(
                    "That player is no longer in the lobby.",
                    ephemeral=True,
                )

                return

            await self.lobby_view.runtime.runner.lobbies.kick(
                session_id=self.session_id,
                host_id=interaction.user.id,
                target_id=target_id,
            )

            await self.lobby_view.refresh_public_message()

            await interaction.response.edit_message(
                content=(
                    f"✅ **{target.username}** "
                    f"was removed from the lobby."
                ),
                view=None,
            )

        except Exception:

            logger.exception(
                "Lobby kick failed."
            )

            await send_error(
                interaction,
                t(
                    "generic_error",
                    self.lobby_view.language,
                ),
            )

    async def previous_page(
        self,
        interaction: discord.Interaction,
    ):

        self.page -= 1
        self.build_select()

        await interaction.response.edit_message(
            view=self,
        )

    async def next_page(
        self,
        interaction: discord.Interaction,
    ):

        self.page += 1
        self.build_select()

        await interaction.response.edit_message(
            view=self,
        )


# =========================================================
# MUSICAL ROULETTE LOBBY VIEW
# =========================================================

class MusicalRouletteLobbyView(discord.ui.View):
    """Discord lobby controls for Musical Roulette."""

    def __init__(
        self,
        runtime: V3Runtime,
        session_id: str,
        language: str = "en",
        cleanup_manager=None,
    ) -> None:

        super().__init__(timeout=900)

        self.runtime = runtime
        self.session_id = session_id
        self.language = language
        self.cleanup_manager = cleanup_manager

        self.message = None
        self.closed = False
        self.superseded = False

        self.join_button.label = t(
            "roulette_join",
            language,
        )

        self.leave_button.label = t(
            "roulette_leave",
            language,
        )

        self.start_button.label = t(
            "roulette_start",
            language,
        )

        self.close_button.label = t(
            "roulette_close",
            language,
        )

    async def refresh_public_message(self):

        session = await self.runtime.runner.lobbies.get(
            self.session_id
        )

        if self.message is None:
            return

        if (
            session is None
            or session.status.value != "lobby"
        ):

            self.closed = True

            for item in self.children:
                item.disabled = True

            try:
                await self.message.edit(
                    content=t(
                        "roulette_unavailable",
                        self.language,
                    ),
                    embed=None,
                    view=self,
                )

                schedule_finished_game_message(
                    self.cleanup_manager,
                    self.message,
                    self.session_id,
                )

            except discord.HTTPException:
                logger.exception(
                    "Could not update unavailable roulette lobby."
                )

            return

        await self.message.edit(
            embed=build_roulette_lobby_embed(
                session,
                self.language,
            ),
            view=self,
        )

    async def refresh(
        self,
        interaction: discord.Interaction,
    ):

        session = await self.runtime.runner.lobbies.get(
            self.session_id
        )

        if (
            session is None
            or session.status.value != "lobby"
        ):

            self.closed = True

            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                content=t(
                    "roulette_unavailable",
                    self.language,
                ),
                embed=None,
                view=self,
            )

            schedule_finished_game_message(
                self.cleanup_manager,
                interaction.message,
                self.session_id,
            )

            return

        await interaction.response.edit_message(
            embed=build_roulette_lobby_embed(
                session,
                self.language,
            ),
            view=self,
        )

    async def host_only(
        self,
        interaction: discord.Interaction,
    ):

        session = await self.runtime.runner.lobbies.get(
            self.session_id
        )

        if session is None:

            await send_error(
                interaction,
                t(
                    "roulette_unavailable",
                    self.language,
                ),
            )

            return None

        if str(interaction.user.id) != str(session.host_id):

            await send_error(
                interaction,
                t(
                    "roulette_host_only",
                    self.language,
                ),
            )

            return None

        return session

    @discord.ui.button(
        label="Join",
        emoji="➕",
        style=discord.ButtonStyle.success,
    )
    async def join_button(
        self,
        interaction,
        button,
    ):

        try:

            await self.runtime.runner.lobbies.join(
                session_id=self.session_id,
                user_id=interaction.user.id,
                username=interaction.user.display_name,
            )

            await self.refresh(interaction)

        except Exception:

            logger.exception(
                "Musical Roulette join failed."
            )

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    @discord.ui.button(
        label="Leave",
        emoji="➖",
        style=discord.ButtonStyle.secondary,
    )
    async def leave_button(
        self,
        interaction,
        button,
    ):

        try:

            await self.runtime.runner.lobbies.leave(
                session_id=self.session_id,
                user_id=interaction.user.id,
            )

            await self.refresh(interaction)

        except Exception:

            logger.exception(
                "Musical Roulette leave failed."
            )

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    @discord.ui.button(
        label="Capacity",
        emoji="👥",
        style=discord.ButtonStyle.secondary,
    )
    async def capacity_button(
        self,
        interaction,
        button,
    ):

        session = await self.host_only(interaction)

        if session is None:
            return

        await interaction.response.send_modal(
            RouletteCapacityModal(
                self,
                session.max_players,
            )
        )

    @discord.ui.button(
        label="Kick Player",
        emoji="👢",
        style=discord.ButtonStyle.danger,
    )
    async def kick_button(
        self,
        interaction,
        button,
    ):

        session = await self.host_only(interaction)

        if session is None:
            return

        players = [
            player
            for player in session.players.values()
            if str(player.user_id) != str(session.host_id)
        ]

        if not players:

            await interaction.response.send_message(
                "There are no players to remove.",
                ephemeral=True,
            )

            return

        view = RouletteKickView(
            self,
            session,
        )

        await interaction.response.send_message(
            "Select the player you want to remove:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Start Game",
        emoji="🚀",
        style=discord.ButtonStyle.primary,
    )
    async def start_button(
        self,
        interaction,
        button,
    ):

        session = await self.host_only(interaction)

        if session is None:
            return

        try:

            launch = await self.runtime.runner.start_multiplayer_game(
                session_id=self.session_id,
                host_id=interaction.user.id,
            )

            if launch.handler is None:
                raise RuntimeError(
                    "Musical Roulette handler is unavailable."
                )

            game_view = MusicalRouletteGameView(
                handler=launch.handler,
                language=self.language,
                cleanup_manager=self.cleanup_manager,
            )

            game_view.message = interaction.message
            self.superseded = True

            await interaction.response.edit_message(
                embed=build_roulette_game_embed(
                    launch.handler,
                    self.language,
                ),
                view=game_view,
            )

        except Exception:

            logger.exception(
                "Musical Roulette launch failed."
            )

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    @discord.ui.button(
        label="Close Lobby",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
    )
    async def close_button(
        self,
        interaction,
        button,
    ):

        session = await self.host_only(interaction)

        if session is None:
            return

        try:

            await self.runtime.runner.lobbies.close(
                session_id=self.session_id,
                host_id=interaction.user.id,
            )

            self.closed = True

            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                content=t(
                    "roulette_closed",
                    self.language,
                ),
                embed=None,
                view=self,
            )

            schedule_finished_game_message(
                self.cleanup_manager,
                interaction.message,
                self.session_id,
            )

        except Exception:

            logger.exception(
                "Musical Roulette close failed."
            )

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    async def on_timeout(self):

        if self.superseded or self.closed:
            return

        self.closed = True

        for item in self.children:
            item.disabled = True

        if self.message is not None:

            try:
                await self.message.edit(view=self)

                schedule_finished_game_message(
                    self.cleanup_manager,
                    self.message,
                    self.session_id,
                )

            except discord.HTTPException:
                logger.exception(
                    "Could not finalize timed-out roulette lobby."
                )


# =========================================================
# MUSICAL ROULETTE GAME VIEW
# =========================================================

class MusicalRouletteGameView(discord.ui.View):
    """Turn-based target selection controls."""

    def __init__(
        self,
        handler,
        language: str = "en",
        cleanup_manager=None,
    ) -> None:

        super().__init__(timeout=600)

        self.handler = handler
        self.language = language
        self.cleanup_manager = cleanup_manager

        self.message = None
        self.superseded = False
        self.finished = False

        self._build_target_buttons()

    def _build_target_buttons(self) -> None:

        self.clear_items()

        if self.handler.is_finished:
            return

        try:
            targets = self.handler.get_available_targets()
        except Exception:

            logger.exception(
                "Could not load Musical Roulette targets."
            )

            targets = ()

        for target in targets:

            button = discord.ui.Button(
                label=safe_text(target.username, 70),
                emoji="❌",
                style=discord.ButtonStyle.danger,
                custom_id=(
                    f"mr:{self.handler.session.session_id}:"
                    f"{target.user_id}"
                ),
            )

            async def select_target(
                interaction: discord.Interaction,
                target_id: str = str(target.user_id),
            ) -> None:

                await self._select_target(
                    interaction,
                    target_id,
                )

            button.callback = select_target
            self.add_item(button)

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        chooser_id = self.handler.current_chooser_id

        if str(interaction.user.id) != str(chooser_id):

            await interaction.response.send_message(
                t(
                    "roulette_wait_turn",
                    self.language,
                ),
                ephemeral=True,
            )

            return False

        return True

    async def _select_target(
        self,
        interaction: discord.Interaction,
        target_id: str,
    ) -> None:

        try:

            await self.handler.eliminate(
                chooser_id=interaction.user.id,
                target_id=target_id,
            )

            if self.handler.is_finished:

                self.finished = True
                self.superseded = True

                await interaction.response.edit_message(
                    embed=build_roulette_game_embed(
                        self.handler,
                        self.language,
                    ),
                    view=None,
                )

                schedule_finished_game_message(
                    self.cleanup_manager,
                    interaction.message,
                    str(self.handler.session.session_id),
                )

                return

            next_view = MusicalRouletteGameView(
                handler=self.handler,
                language=self.language,
                cleanup_manager=self.cleanup_manager,
            )

            next_view.message = interaction.message
            self.superseded = True

            await interaction.response.edit_message(
                embed=build_roulette_game_embed(
                    self.handler,
                    self.language,
                ),
                view=next_view,
            )

        except Exception:

            logger.exception(
                "Musical Roulette elimination failed."
            )

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    async def on_timeout(self) -> None:

        if self.superseded or self.finished:
            return

        self.finished = True

        for item in self.children:
            item.disabled = True

        if self.message is not None:

            try:

                await self.message.edit(
                    content="⏰ Musical Roulette has ended because the game timed out.",
                    view=self,
                )

                schedule_finished_game_message(
                    self.cleanup_manager,
                    self.message,
                    str(self.handler.session.session_id),
                )

            except discord.HTTPException:
                logger.exception(
                    "Could not finalize timed-out Musical Roulette game."
                )


# =========================================================
# V3 DISCORD COMMANDS
# =========================================================

class V3Games(commands.Cog):
    """Discord commands for MHN ARCADE V3."""

    def __init__(
        self,
        bot: commands.Bot,
        runtime: V3Runtime,
    ) -> None:

        self.bot = bot
        self.runtime = runtime

        # The cleanup manager is created by main.py.
        cleanup_manager = getattr(
            bot,
            "message_cleanup",
            None,
        )

        # Shared lifecycle manager for every V3 game.
        self.message_lifecycle = DiscordMessageLifecycle(
            cleanup_manager=cleanup_manager,
        )

        # Connect engine lifecycle events to Discord.
        self.runtime.set_session_lifecycle_callback(
            self.message_lifecycle.on_session_lifecycle
        )

        self.runtime.achievement_announcement_callback = (
            self._announce_achievements
        )

    async def _announce_achievements(
        self,
        unlocked: list[dict[str, str]],
    ) -> None:

        channel = self.bot.get_channel(
            ACHIEVEMENTS_CHANNEL_ID
        )

        if channel is None:

            try:
                channel = await self.bot.fetch_channel(
                    ACHIEVEMENTS_CHANNEL_ID
                )
            except discord.HTTPException:

                logger.exception(
                    "Could not find the V3 achievements channel."
                )

                return

        for item in unlocked:

            user_id = item["user_id"]
            username = item["username"]

            name_ar = item["name_ar"]
            name_en = item["name_en"]

            description_ar = item["description_ar"]
            description_en = item["description_en"]

            rarity = item["rarity"]

            message = (
                "🏆 **MHN ARCADE V3 — ACHIEVEMENT UNLOCKED!**\n\n"
                f"👤 Player: <@{user_id}> (`{username}`)\n"
                f"💎 **{name_en}**\n"
                f"📝 {description_en}\n"
                f"⭐ Rarity: **{rarity}**\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "🏆 **تم فتح إنجاز جديد!**\n\n"
                f"👤 اللاعب: <@{user_id}>\n"
                f"💎 **{name_ar}**\n"
                f"📝 {description_ar}\n"
                f"⭐ الندرة: **{rarity}**\n\n"
                "🔥 Keep playing. Your legacy starts here!\n"
                "🔥 استمر باللعب، إنجازاتك تصنع تاريخك!"
            )

            try:

                await channel.send(
                    message,
                    allowed_mentions=discord.AllowedMentions(
                        users=True,
                        roles=False,
                        everyone=False,
                    ),
                )

            except discord.HTTPException:

                logger.exception(
                    "Failed to announce achievement %s for player %s.",
                    item["achievement_id"],
                    user_id,
                )

    # -----------------------------------------------------
    # GAME CATALOG
    # -----------------------------------------------------

    @app_commands.command(
        name="arcade_v3",
        description="Open the MHN ARCADE V3 game catalog.",
    )
    @app_commands.guild_only()
    async def arcade_v3(
        self,
        interaction: discord.Interaction,
    ) -> None:

        language = resolve_language(interaction)

        if interaction.guild is None:

            await interaction.response.send_message(
                t("server_only", language),
                ephemeral=True,
            )

            return

        try:

            self.runtime.require_initialized()

            games = self.runtime.runner.list_games()

            pages = build_catalog_pages(
                games,
                language,
            )

            view = CatalogView(
                pages=pages,
                owner_id=interaction.user.id,
                language=language,
            )

            await interaction.response.send_message(
                embed=pages[0],
                view=view,
                ephemeral=True,
            )

            view.message = await interaction.original_response()

        except Exception:

            logger.exception(
                "V3 catalog command failed."
            )

            await send_error(
                interaction,
                t("catalog_error", language),
            )

    # -----------------------------------------------------
    # COIN FLIP
    # -----------------------------------------------------

    @app_commands.command(
        name="coin_flip",
        description="Play Coin Flip in MHN ARCADE V3.",
    )
    @app_commands.guild_only()
    async def coin_flip(
        self,
        interaction: discord.Interaction,
    ) -> None:

        language = resolve_language(interaction)

        try:

            self.runtime.require_initialized()

            launch = await self.runtime.runner.prepare_single_player_game(
                game_id="coin_flip",
                player_id=str(interaction.user.id),
                player_name=interaction.user.display_name,
            )

            if launch.handler is None:
                raise RuntimeError(
                    "Coin Flip handler is not available."
                )

            view = CoinFlipView(
                handler=launch.handler,
                owner_id=interaction.user.id,
                language=language,
                cleanup_manager=self.message_lifecycle,
            )

            # Public game message.
            await interaction.response.send_message(
                embed=build_coin_flip_embed(
                    language=language,
                ),
                view=view,
            )

            view.message = await interaction.original_response()

        except Exception:

            logger.exception(
                "V3 Coin Flip command failed."
            )

            await send_error(
                interaction,
                t("coin_flip_error", language),
            )

    # -----------------------------------------------------
    # MUSICAL ROULETTE
    # -----------------------------------------------------

    @app_commands.command(
        name="musical_roulette",
        description="Create a Musical Roulette multiplayer lobby.",
    )
    @app_commands.guild_only()
    async def musical_roulette(
        self,
        interaction: discord.Interaction,
    ) -> None:

        language = resolve_language(interaction)

        if interaction.guild is None:

            await interaction.response.send_message(
                t("server_only", language),
                ephemeral=True,
            )

            return

        try:

            self.runtime.require_initialized()

            session = await self.runtime.runner.create_multiplayer_lobby(
                game_id="musical_roulette",
                guild_id=interaction.guild.id,
                host_id=interaction.user.id,
                host_name=interaction.user.display_name,
            )

            view = MusicalRouletteLobbyView(
                runtime=self.runtime,
                session_id=session.session_id,
                language=language,
                cleanup_manager=self.message_lifecycle,
            )

            await interaction.response.send_message(
                embed=build_roulette_lobby_embed(
                    session,
                    language,
                ),
                view=view,
            )

            view.message = await interaction.original_response()

            # Bind the public lobby message to its session.
            self.message_lifecycle.bind_session_message(
                session_id=session.session_id,
                message=view.message,
            )

        except Exception:

            logger.exception(
                "Musical Roulette lobby creation failed."
            )

            await send_error(
                interaction,
                t("generic_error", language),
            )


# =========================================================
# EXTENSION SETUP
# =========================================================

async def setup(bot: commands.Bot) -> None:
    """Initialize V3 and register its Discord commands."""

    runtime = V3Runtime()

    try:

        await runtime.initialize()

        cog = V3Games(
            bot=bot,
            runtime=runtime,
        )

        await bot.add_cog(cog)

        bot.v3_runtime = runtime
        bot.v3_message_lifecycle = cog.message_lifecycle

        logger.info(
            "MHN ARCADE V3 Discord extension loaded."
        )

    except Exception:

        await runtime.shutdown()
        raise


async def teardown(bot: commands.Bot) -> None:
    """Cleanly shut down the V3 runtime."""

    lifecycle = getattr(
        bot,
        "v3_message_lifecycle",
        None,
    )

    if lifecycle is not None:
        lifecycle.clear()

        delattr(
            bot,
            "v3_message_lifecycle",
        )

    runtime = getattr(
        bot,
        "v3_runtime",
        None,
    )

    if runtime is not None:

        await runtime.shutdown()

        delattr(
            bot,
            "v3_runtime",
        )

        logger.info(
            "MHN ARCADE V3 runtime shut down."
        )
