
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


logger = logging.getLogger("mhn.arcade.v3.discord")
ACHIEVEMENTS_CHANNEL_ID = 1567722630969303090
PURPLE = 0x7C3AED
GAMES_PER_PAGE = 4
DESCRIPTION_LIMIT = 550


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
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


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
                }.get(mode_value, mode_value.replace("_", " "))
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
            footer = f"MHN ARCADE V3 • الصفحة {page_number}/{total_pages}"
        else:
            footer = f"MHN ARCADE V3 • Page {page_number}/{total_pages}"

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
        emoji = "🌕" if result.side == "heads" else "🌑"

        side_key = (
            "coin_flip_heads"
            if result.side == "heads"
            else "coin_flip_tails"
        )

        side_name = t(side_key, language)

        if language == "ar":
            result_value = side_name
        else:
            result_value = side_name

        embed.add_field(
            name=f"{emoji} {t('coin_flip_result', language)}",
            value=f"**{result_value}**",
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

    embed.set_footer(text="MHN ARCADE V3 • Coin Flip")
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
            embed.description = t("roulette_draw", language)

        elif winner:
            embed.description = (
                f"🏆 **{t('roulette_winner', language)}:** "
                f"<@{winner['user_id']}>\n"
                f"{t('roulette_congratulations', language)}"
            )

        else:
            embed.description = t("roulette_ended", language)

    else:
        chooser_id = state.get("current_chooser_id")

        embed.description = (
            f"🎯 **{t('roulette_round', language)}:** "
            f"{state['round']}\n"
            f"🗣️ **{t('roulette_current_chooser', language)}:** "
            f"<@{chooser_id}>\n\n"
            f"{t('roulette_choose_player', language)}"
        )

    remaining = state.get("remaining_players", [])

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

    eliminations = state.get("eliminations", [])

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

    embed.set_footer(text="MHN ARCADE V3 • Musical Roulette")
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

        self.previous_button.label = t("previous", language)
        self.next_button.label = t("next", language)

        self.update_buttons()

    def update_buttons(self) -> None:
        self.previous_button.disabled = self.current_page <= 0
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
    ) -> None:

        super().__init__(timeout=300)

        self.handler = handler
        self.owner_id = owner_id
        self.language = language
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
            logger.exception("Coin Flip action failed.")

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    async def on_timeout(self) -> None:

        self.finished = True

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


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
    ) -> None:

        super().__init__(timeout=900)

        self.runtime = runtime
        self.session_id = session_id
        self.language = language
        self.message = None
        self.closed = False
        self.superseded = False
        self.join_button.label = t("roulette_join", language)
        self.leave_button.label = t("roulette_leave", language)
        self.start_button.label = t("roulette_start", language)
        self.close_button.label = t("roulette_close", language)

    async def refresh(
        self,
        interaction: discord.Interaction,
    ) -> None:

        session = await self.runtime.runner.lobbies.get(
            self.session_id
        )

        if session is None or session.status.value != "lobby":
            self.closed = True

            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                content=t("roulette_unavailable", self.language),
                embed=None,
                view=self,
            )
            return

        await interaction.response.edit_message(
            embed=build_roulette_lobby_embed(
                session,
                self.language,
            ),
            view=self,
        )

    @discord.ui.button(
        label="Join",
        emoji="➕",
        style=discord.ButtonStyle.success,
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        try:
            await self.runtime.runner.lobbies.join(
                session_id=self.session_id,
                user_id=interaction.user.id,
                username=interaction.user.display_name,
            )

            await self.refresh(interaction)

        except Exception:
            logger.exception("Musical Roulette join failed.")

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
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        try:
            await self.runtime.runner.lobbies.leave(
                session_id=self.session_id,
                user_id=interaction.user.id,
            )

            await self.refresh(interaction)

        except Exception:
            logger.exception("Musical Roulette leave failed.")

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    @discord.ui.button(
        label="Start Game",
        emoji="🚀",
        style=discord.ButtonStyle.primary,
    )
    async def start_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        session = await self.runtime.runner.lobbies.get(
            self.session_id
        )

        if session is None:
            await send_error(
                interaction,
                t("roulette_unavailable", self.language),
            )
            return

        if str(interaction.user.id) != str(session.host_id):
            await send_error(
                interaction,
                t("roulette_host_only", self.language),
            )
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
                launch.handler,
                language=self.language,
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
            logger.exception("Musical Roulette launch failed.")

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
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        session = await self.runtime.runner.lobbies.get(
            self.session_id
        )

        if session is None:
            await send_error(
                interaction,
                t("roulette_unavailable", self.language),
            )
            return

        if str(interaction.user.id) != str(session.host_id):
            await send_error(
                interaction,
                t("roulette_host_only", self.language),
            )
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
                content=t("roulette_closed", self.language),
                embed=None,
                view=self,
            )

        except Exception:
            logger.exception("Musical Roulette close failed.")

            await send_error(
                interaction,
                t("generic_error", self.language),
            )

    async def on_timeout(self) -> None:
        if self.superseded:
            return

        for item in self.children:
            item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


# =========================================================
# MUSICAL ROULETTE GAME VIEW
# =========================================================

class MusicalRouletteGameView(discord.ui.View):
    """Turn-based target selection controls."""

    def __init__(
        self,
        handler,
        language: str = "en",
    ) -> None:

        super().__init__(timeout=600)

        self.handler = handler
        self.language = language
        self.message = None
        self.superseded = False
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
                t("roulette_wait_turn", self.language),
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
                self.superseded = True
                await interaction.response.edit_message(
                    embed=build_roulette_game_embed(
                        self.handler,
                        self.language,
                    ),
                    view=None,
                )
                return

            next_view = MusicalRouletteGameView(
                self.handler,
                language=self.language,
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
        if self.superseded:
            return
        for item in self.children:
            item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


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
            logger.exception("V3 catalog command failed.")

            await send_error(
                interaction,
                t("catalog_error", language),
            )

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
            )

            await interaction.response.send_message(
                embed=build_coin_flip_embed(
                    language=language,
                ),
                view=view,
                ephemeral=True,
            )

            view.message = await interaction.original_response()

        except Exception:
            logger.exception("V3 Coin Flip command failed.")

            await send_error(
                interaction,
                t("coin_flip_error", language),
            )

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
            )

            await interaction.response.send_message(
                embed=build_roulette_lobby_embed(
                    session,
                    language,
                ),
                view=view,
            )

            view.message = await interaction.original_response()

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

        logger.info(
            "MHN ARCADE V3 Discord extension loaded."
        )

    except Exception:
        await runtime.shutdown()
        raise


async def teardown(bot: commands.Bot) -> None:
    """Cleanly shut down the V3 runtime."""

    runtime = getattr(
        bot,
        "v3_runtime",
        None,
    )

    if runtime is not None:
        await runtime.shutdown()
        delattr(bot, "v3_runtime")

        logger.info(
            "MHN ARCADE V3 runtime shut down."
        )
