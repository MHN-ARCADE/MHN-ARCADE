"""
MHN ARCADE V3 - Discord Integration

A separate Discord extension for the V3 engine.
This module does not modify the existing V2 systems.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from engine.runtime import V3Runtime


logger = logging.getLogger("mhn.arcade.v3.discord")

PURPLE = 0x7C3AED


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
        description="Open the MHN ARCADE V3 game catalog."
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

            embed = discord.Embed(
                title="💜 MHN ARCADE V3",
                description=(
                    "Welcome to the next generation of MHN ARCADE!\n\n"
                    "Choose your next challenge from the V3 game engine."
                ),
                color=PURPLE,
            )

            for game in games:
                mode = game.mode.value.replace("_", " ").title()

                embed.add_field(
                    name=f"🎮 {game.name_en} | {game.name_ar}",
                    value=(
                        f"**Game ID:** `{game.game_id}`\n"
                        f"**Mode:** {mode}\n"
                        f"{game.description_en}"
                    ),
                    inline=False,
                )

            embed.set_footer(
                text="MHN ARCADE V3 • PLAY • COMPETE • WIN"
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        except Exception:
            logger.exception("V3 catalog command failed.")

            await interaction.response.send_message(
                "تعذر تحميل قائمة ألعاب V3 حاليًا.",
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
