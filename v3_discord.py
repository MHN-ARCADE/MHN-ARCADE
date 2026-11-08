
"""
MHN ARCADE V3 - Discord Integration

V3 game catalog and interactive Discord game interfaces.
Kept separate from the existing V2 systems.
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
    """Keep text within Discord embed limits."""
    value = str(value or "").strip()

    if len(value) <= limit:
        return value

    return value[:limit - 3] + "..."


def build_catalog_pages(games: tuple) -> list[discord.Embed]:
    """Build paginated embeds for the V3 game catalog."""

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
        page_games = games[
            page_index:page_index + GAMES_PER_PAGE
        ]

        page_number = page_index // GAMES_PER_PAGE + 1
        total_pages = (
            len(games) + GAMES_PER_PAGE - 1
        ) // GAMES_PER_PAGE

        embed = discord.Embed(
            title="💜 MHN ARCADE V3",
            description=(
                "Welcome to the next generation of MHN ARCADE!\n\n"
                "Explore the available games below."
            ),
            color=PURPLE,
        )

        for game in page_games:
            mode = game.mode.value.replace(
                "_", " "
            ).title()

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
                f"**Players:** "
                f"{game.min_players}-{game.max_players}\n"
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
    """Build the Coin Flip game display."""

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

        english_side = (
            "Heads" if result.side == "heads" else "Tails"
        )

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


class CatalogView(discord.ui.View):
    """Interactive pagination for the V3 game catalog."""

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
        self.next_button.disabled = (
            self.current_page >= len(self.pages) - 1
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
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
    """Owner-controlled interactive Coin Flip game."""

    def __init__(
        self,
        handler,
        owner_id: int,
    ) -> None:
        super().__init__(timeout=300)

        self.handler = handler
        self.owner_id = owner_id
        self.message = None
        self.finished = False

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
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

            await interaction.response.send_message(
                "تعذر رمي العملة حاليًا. حاول مرة أخرى.",
                ephemeral=True,
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


class V3Games(commands.Cog):
    """Discord commands for MHN ARCADE V3."""

    def __init__(
        self,
        bot: commands.Bot,
        runtime: V3Runtime,
    ) -> None:
        self.bot = bot
        self.runtime = runtime

    @app_commands.command(
        name="arcade_v3",
        description="Open the MHN ARCADE V3 game catalog.",
    )
    @app_commands.guild_only()
    async def arcade_v3(
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

            games = self.runtime.runner.list_games()
            pages = build_catalog_pages(games)

            view = CatalogView(
                pages=pages,
                owner_id=interaction.user.id,
            )

            await interaction.response.send_message(
                embed=pages[0],
                view=view,
                ephemeral=True,
            )

            view.message = await interaction.original_response()

        except Exception:
            logger.exception("V3 catalog command failed.")

            if interaction.response.is_done():
                await interaction.followup.send(
                    "تعذر تحميل قائمة ألعاب V3 حاليًا.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "تعذر تحميل قائمة ألعاب V3 حاليًا.",
                    ephemeral=True,
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
            )

            embed = build_coin_flip_embed()

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True,
            )

            view.message = await interaction.original_response()

        except Exception:
            logger.exception("V3 Coin Flip command failed.")

            if interaction.response.is_done():
                await interaction.followup.send(
                    "تعذر تشغيل Coin Flip حاليًا.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "تعذر تشغيل Coin Flip حاليًا.",
                    ephemeral=True,
                )


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
