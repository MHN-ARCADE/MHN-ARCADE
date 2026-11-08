
"""
MHN ARCADE V3 - Discord Integration

Interactive Discord interfaces for the V3 game engine.
The V2 systems remain separate and unchanged.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from engine.runtime import V3Runtime


logger = logging.getLogger("mhn.arcade.v3.discord")

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


def build_catalog_pages(games: tuple) -> list[discord.Embed]:
    if not games:
        embed = discord.Embed(
            title="💜 MHN ARCADE V3",
            description="No games are currently registered.",
            color=PURPLE,
        )
        embed.set_footer(text="MHN ARCADE V3")
        return [embed]

    pages = []

    for page_index in range(0, len(games), GAMES_PER_PAGE):
        page_games = games[page_index:page_index + GAMES_PER_PAGE]
        page_number = page_index // GAMES_PER_PAGE + 1
        total_pages = (len(games) + GAMES_PER_PAGE - 1) // GAMES_PER_PAGE

        embed = discord.Embed(
            title="💜 MHN ARCADE V3",
            description=(
                "Welcome to the next generation of MHN ARCADE!\n\n"
                "Explore the available games below."
            ),
            color=PURPLE,
        )

        for game in page_games:
            mode = game.mode.value.replace("_", " ").title()
            game_name = safe_text(
                f"{game.name_en} | {game.name_ar}",
                250,
            )
            description = safe_text(
                game.description_en,
                DESCRIPTION_LIMIT,
            )
            field_value = (
                f"**Game ID:** `{game.game_id}`\n"
                f"**Mode:** {mode}\n"
                f"**Players:** {game.min_players}-{game.max_players}\n"
                f"{description}"
            )
            embed.add_field(
                name=f"🎮 {game_name}",
                value=safe_text(field_value, 1024),
                inline=False,
            )

        embed.set_footer(
            text=f"MHN ARCADE V3 • Page {page_number}/{total_pages}"
        )
        pages.append(embed)

    return pages


def build_coin_flip_embed(result=None, total_flips: int = 0):
    embed = discord.Embed(
        title="🪙 MHN ARCADE V3 • Coin Flip",
        description=(
            "اختر وقت ما تبي، واضغط الزر لرمي العملة!\n"
            "Flip the coin and test your luck."
        ),
        color=PURPLE,
    )

    if result is None:
        embed.add_field(
            name="🎯 Result",
            value="Waiting for your first flip...",
            inline=False,
        )
    else:
        emoji = "🌕" if result.side == "heads" else "🌑"
        english_side = "Heads" if result.side == "heads" else "Tails"
        embed.add_field(
            name=f"{emoji} {english_side}",
            value=f"**النتيجة:** {result.side_ar}",
            inline=False,
        )
        embed.add_field(
            name="🔢 Flip Number",
            value=str(result.flip_number),
            inline=True,
        )

    embed.add_field(
        name="📊 Total Flips",
        value=str(total_flips),
        inline=True,
    )
    embed.set_footer(text="MHN ARCADE V3 • Coin Flip")
    return embed


def build_roulette_lobby_embed(session: discord.Object) -> discord.Embed:
    players = list(session.players.values())
    player_lines = []

    for player in players:
        marker = "👑" if player.user_id == session.host_id else "🎮"
        player_lines.append(f"{marker} **{safe_text(player.username, 60)}**")

    embed = discord.Embed(
        title="🎵 MHN ARCADE V3 • Musical Roulette",
        description=(
            "انضموا إلى اللوبي واستعدوا للمواجهة!\n"
            "Join the lobby and get ready to play."
        ),
        color=PURPLE,
    )
    embed.add_field(
        name=f"👥 Players ({session.player_count}/{session.max_players})",
        value="\n".join(player_lines) if player_lines else "No players yet.",
        inline=False,
    )
    embed.add_field(
        name="🎯 Requirements",
        value=f"Minimum: **{session.min_players}** players",
        inline=True,
    )
    embed.add_field(
        name="👑 Host",
        value=f"<@{session.host_id}>",
        inline=True,
    )
    embed.set_footer(
        text=f"Lobby ID: {session.session_id} • MHN ARCADE V3"
    )
    return embed


def build_roulette_game_embed(handler) -> discord.Embed:
    state = handler.get_state()
    embed = discord.Embed(
        title="🎵 MHN ARCADE V3 • Musical Roulette",
        color=PURPLE,
    )

    if state["finished"]:
        winner = state.get("winner")
        if state.get("is_draw"):
            embed.description = "🤝 **It's a draw!** No player remains."
        elif winner:
            embed.description = (
                f"🏆 **Winner:** <@{winner['user_id']}>\n"
                f"Congratulations!"
            )
        else:
            embed.description = "The match has ended."

    else:
        chooser_id = state.get("current_chooser_id")
        embed.description = (
            f"🎯 **Round:** {state['round']}\n"
            f"🗣️ **Current chooser:** <@{chooser_id}>\n\n"
            "The current chooser must select a player to eliminate."
        )

    remaining = state.get("remaining_players", [])
    remaining_text = "\n".join(
        f"🟢 <@{player['user_id']}>"
        for player in remaining
    )
    embed.add_field(
        name=f"👥 Remaining Players ({len(remaining)})",
        value=remaining_text or "No players remaining.",
        inline=False,
    )

    eliminations = state.get("eliminations", [])
    if eliminations:
        recent = eliminations[-8:]
        history = "\n".join(
            f"❌ <@{item['eliminated_id']}> — chosen by "
            f"<@{item['chosen_by_id']}>"
            for item in recent
        )
        embed.add_field(
            name="📜 Elimination History",
            value=history,
            inline=False,
        )

    embed.set_footer(text="MHN ARCADE V3 • Musical Roulette")
    return embed


class CatalogView(discord.ui.View):
    def __init__(
        self,
        pages: list[discord.Embed],
        owner_id: int,
    ) -> None:
        super().__init__(timeout=180)
        self.pages = pages
        self.owner_id = owner_id
        self.current_page = 0
        self.message = None
        self.update_buttons()

    def update_buttons(self) -> None:
        self.previous_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "هذه القائمة مخصصة للشخص الذي فتحها.",
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
        self.current_page = max(0, self.current_page - 1)
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


class CoinFlipView(discord.ui.View):
    def __init__(self, handler, owner_id: int) -> None:
        super().__init__(timeout=300)
        self.handler = handler
        self.owner_id = owner_id
        self.message = None
        self.finished = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "هذه اللعبة مخصصة للشخص الذي بدأها.",
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
                "انتهت هذه اللعبة.",
                ephemeral=True,
            )
            return

        try:
            result = self.handler.flip()
            embed = build_coin_flip_embed(
                result=result,
                total_flips=self.handler.total_flips,
            )
            await interaction.response.edit_message(
                embed=embed,
                view=self,
            )
        except Exception:
            logger.exception("Coin Flip action failed.")
            await send_error(
                interaction,
                "تعذر رمي العملة حاليًا. حاول مرة أخرى.",
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


class MusicalRouletteLobbyView(discord.ui.View):
    """Discord lobby controls for Musical Roulette."""

    def __init__(self, runtime: V3Runtime, session_id: str) -> None:
        super().__init__(timeout=900)
        self.runtime = runtime
        self.session_id = session_id
        self.message = None
        self.closed = False

    async def refresh(self, interaction: discord.Interaction) -> None:
        session = await self.runtime.runner.lobbies.get(self.session_id)

        if session is None or session.status.value != "lobby":
            self.closed = True
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                content="This lobby is no longer available.",
                embed=None,
                view=self,
            )
            return

        await interaction.response.edit_message(
            embed=build_roulette_lobby_embed(session),
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
        except Exception as exc:
            await send_error(interaction, safe_text(str(exc), 180))

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
        except Exception as exc:
            await send_error(interaction, safe_text(str(exc), 180))

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
        session = await self.runtime.runner.lobbies.get(self.session_id)

        if session is None:
            await send_error(interaction, "This lobby is no longer available.")
            return

        if str(interaction.user.id) != session.host_id:
            await send_error(interaction, "Only the lobby host can start the game.")
            return

        try:
            launch = await self.runtime.runner.start_multiplayer_game(
                session_id=self.session_id,
                host_id=interaction.user.id,
            )
            if launch.handler is None:
                raise RuntimeError("Musical Roulette handler is unavailable.")

            game_view = MusicalRouletteGameView(launch.handler)
            game_view.message = interaction.message

            await interaction.response.edit_message(
                embed=build_roulette_game_embed(launch.handler),
                view=game_view,
            )
        except Exception as exc:
            logger.exception("Musical Roulette launch failed.")
            await send_error(interaction, safe_text(str(exc), 180))

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
        session = await self.runtime.runner.lobbies.get(self.session_id)

        if session is None:
            await send_error(interaction, "This lobby is already closed.")
            return

        if str(interaction.user.id) != session.host_id:
            await send_error(interaction, "Only the lobby host can close it.")
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
                content="🔒 Musical Roulette lobby closed by the host.",
                embed=None,
                view=self,
            )
        except Exception as exc:
            await send_error(interaction, safe_text(str(exc), 180))

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class MusicalRouletteGameView(discord.ui.View):
    """Turn-based target selection controls."""

    def __init__(self, handler) -> None:
        super().__init__(timeout=600)
        self.handler = handler
        self.message = None
        self._build_target_buttons()

    def _build_target_buttons(self) -> None:
        self.clear_items()

        if self.handler.is_finished:
            return

        try:
            targets = self.handler.get_available_targets()
        except Exception:
            targets = ()

        for target in targets:
            button = discord.ui.Button(
                label=safe_text(target.username, 70),
                emoji="❌",
                style=discord.ButtonStyle.danger,
                custom_id=f"mr:{self.handler.session.session_id}:{target.user_id}",
            )

            async def select_target(
                interaction: discord.Interaction,
                target_id: str = target.user_id,
            ) -> None:
                await self._select_target(interaction, target_id)

            button.callback = select_target
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        chooser_id = self.handler.current_chooser_id

        if str(interaction.user.id) != str(chooser_id):
            await interaction.response.send_message(
                "انتظر دورك! اللاعب المحدد حاليًا هو الذي يختار.",
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
                await interaction.response.edit_message(
                    embed=build_roulette_game_embed(self.handler),
                    view=None,
                )
                return

            next_view = MusicalRouletteGameView(self.handler)
            next_view.message = interaction.message

            await interaction.response.edit_message(
                embed=build_roulette_game_embed(self.handler),
                view=next_view,
            )

        except Exception as exc:
            logger.exception("Musical Roulette elimination failed.")
            await send_error(interaction, safe_text(str(exc), 180))

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class V3Games(commands.Cog):
    """Discord commands for MHN ARCADE V3."""

    def __init__(self, bot: commands.Bot, runtime: V3Runtime) -> None:
        self.bot = bot
        self.runtime = runtime

    @app_commands.command(
        name="arcade_v3",
        description="Open the MHN ARCADE V3 game catalog.",
    )
    @app_commands.guild_only()
    async def arcade_v3(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Use this command inside a server.",
                ephemeral=True,
            )
            return

        try:
            self.runtime.require_initialized()
            games = self.runtime.runner.list_games()
            pages = build_catalog_pages(games)
            view = CatalogView(pages=pages, owner_id=interaction.user.id)

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
                "تعذر تحميل قائمة ألعاب V3 حاليًا.",
            )

    @app_commands.command(
        name="coin_flip",
        description="Play Coin Flip in MHN ARCADE V3.",
    )
    @app_commands.guild_only()
    async def coin_flip(self, interaction: discord.Interaction) -> None:
        try:
            self.runtime.require_initialized()
            launch = await self.runtime.runner.prepare_single_player_game(
                game_id="coin_flip",
                player_id=str(interaction.user.id),
                player_name=interaction.user.display_name,
            )

            if launch.handler is None:
                raise RuntimeError("Coin Flip handler is not available.")

            view = CoinFlipView(
                handler=launch.handler,
                owner_id=interaction.user.id,
            )
            await interaction.response.send_message(
                embed=build_coin_flip_embed(),
                view=view,
                ephemeral=True,
            )
            view.message = await interaction.original_response()

        except Exception:
            logger.exception("V3 Coin Flip command failed.")
            await send_error(
                interaction,
                "تعذر تشغيل Coin Flip حاليًا.",
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
        if interaction.guild is None:
            await interaction.response.send_message(
                "Use this command inside a server.",
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
            )

            await interaction.response.send_message(
                embed=build_roulette_lobby_embed(session),
                view=view,
            )
            view.message = await interaction.original_response()

        except Exception as exc:
            logger.exception("Musical Roulette lobby creation failed.")
            await send_error(
                interaction,
                safe_text(str(exc), 180),
            )


async def setup(bot: commands.Bot) -> None:
    """Initialize V3 and register its Discord commands."""
    runtime = V3Runtime()

    try:
        await runtime.initialize()
        cog = V3Games(bot=bot, runtime=runtime)
        await bot.add_cog(cog)
        bot.v3_runtime = runtime
        logger.info("MHN ARCADE V3 Discord extension loaded.")

    except Exception:
        await runtime.shutdown()
        raise


async def teardown(bot: commands.Bot) -> None:
    """Cleanly shut down the V3 runtime."""
    runtime = getattr(bot, "v3_runtime", None)

    if runtime is not None:
        await runtime.shutdown()
        delattr(bot, "v3_runtime")
        logger.info("MHN ARCADE V3 runtime shut down.")
