
"""
========================================================
MHN ARCADE V3
Main Bot Entry Point
========================================================

V3-first Discord application:
- Persistent Arabic and English V3 main menus
- V3 game engine and game catalog
- V3 trophies and player statistics
- V3 player-card panel
- Update announcements and ping utility

Legacy V2 gameplay commands and panels are not loaded here.
Legacy database helpers are retained only where the existing
V3 player-card workflow and saved-message manager still depend
on them. Existing V2 files and data are not deleted.

Environment:
    DISCORD_TOKEN
========================================================
"""

from __future__ import annotations

import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from v3_dashboards import V3DashboardManager
from database import (
    initialize_database,
    get_bot_message,
    save_bot_message,
)
from player_profiles_v3 import initialize_player_profiles
from player_cards_v3 import PlayerCardPanelView as V3PlayerCardPanelView
from v3_menu import V3MainMenuView, create_main_menu_embed


# ========================================================
# CONFIGURATION
# ========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing!")

ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910

PLAYER_CARDS_CHANNEL_ID = 1567719418862112809
ARCADE_NEWS_CHANNEL_ID = 1568381560279933049

PURPLE = 0x7C3AED
VERSION = "V3"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("MHN_ARCADE")


# ========================================================
# DISCORD INTENTS
# ========================================================

intents = discord.Intents.default()
intents.members = True


# ========================================================
# BOT CLASS
# ========================================================

class MHNArcadeBot(commands.Bot):

    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Game(name="MHN ARCADE V3 🎮"),
        )

    async def setup_hook(self) -> None:
        # Initialize the existing database and V3 profiles.
        initialize_database()
        initialize_player_profiles()

        # Load V3. The extension creates bot.v3_runtime.
        await self.load_extension("v3_discord")
        self.v3_dashboards = V3DashboardManager(
            bot=self,
            runtime=self.v3_runtime,
        )
        await self.v3_dashboards.initialize()

        # Register persistent Arabic and English menus.
        self.add_view(
            V3MainMenuView(
                runtime=self.v3_runtime,
                language="ar",
            )
        )

        self.add_view(
            V3MainMenuView(
                runtime=self.v3_runtime,
                language="en",
            )
        )

        self.add_view(V3PlayerCardPanelView())

        synced = await self.tree.sync()

        logger.info(
            "Successfully synchronized %s V3 slash commands.",
            len(synced),
        )


bot = MHNArcadeBot()


# ========================================================
# EMBED AND CHANNEL HELPERS
# ========================================================

def build_embed(
    title: str,
    description: str,
    color: int = PURPLE,
) -> discord.Embed:

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )

    embed.set_footer(
        text=f"MHN ARCADE {VERSION} • PLAY • COMPETE • WIN"
    )

    return embed


async def fetch_text_channel(
    channel_id: int,
) -> discord.TextChannel | None:

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            logger.exception(
                "Could not fetch channel %s",
                channel_id,
            )
            return None

    if not isinstance(channel, discord.TextChannel):
        logger.error(
            "Channel %s is not a text channel.",
            channel_id,
        )
        return None

    return channel


async def ensure_saved_embed_message(
    guild: discord.Guild,
    message_key: str,
    channel_id: int,
    embed: discord.Embed,
    view: discord.ui.View | None = None,
) -> bool:

    channel = await fetch_text_channel(channel_id)

    if channel is None or channel.guild.id != guild.id:
        logger.error(
            "Invalid destination channel for %s",
            message_key,
        )
        return False

    saved = get_bot_message(
        guild.id,
        message_key,
    )

    if saved:
        try:
            old_channel = await bot.fetch_channel(
                int(saved["channel_id"])
            )

            old_message = await old_channel.fetch_message(
                int(saved["message_id"])
            )

            if old_channel.id == channel.id:
                await old_message.edit(
                    embed=embed,
                    view=view,
                )

                logger.info(
                    "Updated saved message: %s",
                    message_key,
                )

                return True

            await old_message.delete()

        except discord.NotFound:
            logger.info(
                "Saved message %s no longer exists.",
                message_key,
            )

        except discord.Forbidden:
            logger.error(
                "No permission to update %s.",
                message_key,
            )
            return False

        except discord.HTTPException:
            logger.exception(
                "Could not update %s.",
                message_key,
            )
            return False

    try:
        message = await channel.send(
            embed=embed,
            view=view,
        )

        save_bot_message(
            guild.id,
            message_key,
            channel.id,
            message.id,
        )

        logger.info(
            "Created saved message: %s",
            message_key,
        )

        return True

    except discord.HTTPException:
        logger.exception(
            "Could not create %s.",
            message_key,
        )
        return False


async def remove_saved_message(
    guild: discord.Guild,
    message_key: str,
) -> None:
    """Delete an obsolete V2 panel without touching player data."""

    saved = get_bot_message(
        guild.id,
        message_key,
    )

    if not saved:
        return

    try:
        channel = await bot.fetch_channel(
            int(saved["channel_id"])
        )

        message = await channel.fetch_message(
            int(saved["message_id"])
        )

        await message.delete()

        logger.info(
            "Removed obsolete panel: %s",
            message_key,
        )

    except discord.NotFound:
        logger.info(
            "Obsolete panel already missing: %s",
            message_key,
        )

    except (
        discord.Forbidden,
        discord.HTTPException,
    ):
        logger.exception(
            "Could not remove obsolete panel: %s",
            message_key,
        )


# ========================================================
# WELCOME MESSAGES
# ========================================================

def create_welcome_embed(
    language: str,
) -> discord.Embed:

    if language == "ar":
        return build_embed(
            "🎮 يا هلا والله في MHN ARCADE V3!",
            (
                "نورت الأركيد يا بطل! 💜\n\n"
                "هنا تبدأ رحلتك في ألعاب MHN ARCADE الجديدة.\n"
                "تصفح الألعاب، نافس اللاعبين، أكمل التحديات "
                "واجمع التروفيات!\n\n"
                "🎮 **مكتبة ألعاب V3**\n"
                "👤 **إحصائيات اللاعب**\n"
                "🏆 **نظام التروفيات والإنجازات**\n"
                "📊 **تقدمك وترتيبك**\n\n"
                "اضغط أزرار القائمة في قناة الألعاب وابدأ!\n"
                "💜 **العب، نافس، واثبت نفسك!**"
            ),
        )

    return build_embed(
        "🎮 Welcome to MHN ARCADE V3!",
        (
            "Your arcade journey starts here! 💜\n\n"
            "Explore the new MHN ARCADE games, compete with "
            "other players, complete challenges, and collect trophies.\n\n"
            "🎮 **V3 Game Library**\n"
            "👤 **Player Statistics**\n"
            "🏆 **Trophies and Achievements**\n"
            "📊 **Your Progress and Ranking**\n\n"
            "Use the menu buttons in your arcade channel to get started.\n"
            "💜 **PLAY • COMPETE • WIN**"
        ),
    )


async def initialize_welcome_messages_for_guild(
    guild: discord.Guild,
) -> bool:

    arabic = await ensure_saved_embed_message(
        guild,
        "welcome_ar",
        ARABIC_ARCADE_CHANNEL_ID,
        create_welcome_embed("ar"),
    )

    english = await ensure_saved_embed_message(
        guild,
        "welcome_en",
        ENGLISH_ARCADE_CHANNEL_ID,
        create_welcome_embed("en"),
    )

    return arabic and english


# ========================================================
# V3 MAIN MENUS AND PLAYER CARD PANEL
# ========================================================

async def initialize_arcade_systems(
    guild: discord.Guild,
) -> None:

    # Arabic V3 main menu.
    await ensure_saved_embed_message(
        guild,
        "guide_ar",
        ARABIC_ARCADE_CHANNEL_ID,
        create_main_menu_embed("ar"),
        view=V3MainMenuView(
            runtime=bot.v3_runtime,
            language="ar",
        ),
    )

    # English V3 main menu.
    await ensure_saved_embed_message(
        guild,
        "guide_en",
        ENGLISH_ARCADE_CHANNEL_ID,
        create_main_menu_embed("en"),
        view=V3MainMenuView(
            runtime=bot.v3_runtime,
            language="en",
        ),
    )

    # V3 player-card panel.
    player_card_panel = build_embed(
        "🎮 بطاقات اللاعبين | Player Cards",
        (
            "اضغط الزر بالأسفل لإنشاء بطاقة لاعبك أو تحديثها. 💜\n"
            "Use the button below to create or update your player card.\n\n"
            "بطاقة واحدة لكل لاعب، بدون تكرار."
        ),
    )

    await ensure_saved_embed_message(
        guild,
        "player_card_panel",
        PLAYER_CARDS_CHANNEL_ID,
        player_card_panel,
        view=V3PlayerCardPanelView(),
    )

    # Remove old V2-only public panels.
    await remove_saved_message(
        guild,
        "leaderboard_panel",
    )

    await remove_saved_message(
        guild,
        "rank_guide",
    )

    logger.info(
        "MHN ARCADE V3 systems initialized for %s",
        guild.name,
    )


# ========================================================
# BOT READY
# ========================================================

@bot.event
async def on_ready() -> None:

    logger.info("=" * 45)
    logger.info("💜 MHN ARCADE V3")
    logger.info("Logged in as: %s", bot.user)
    logger.info("Bot ID: %s", bot.user.id)
    logger.info("Servers: %s", len(bot.guilds))
    logger.info("Status: ONLINE")
    logger.info("=" * 45)

    for guild in bot.guilds:
        try:
            await initialize_welcome_messages_for_guild(guild)
            await initialize_arcade_systems(guild)

        except Exception:
            logger.exception(
                "Failed to initialize V3 systems for %s",
                guild.name,
            )


# ========================================================
# UPDATE ANNOUNCEMENT COMMAND
# ========================================================

@bot.tree.command(
    name="announce_update",
    description="Publish an MHN ARCADE V3 update announcement",
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    version="Update version, for example V3.1",
    additions="New features added in this update",
    improvements="Existing features that were improved",
    fixes="Bugs and issues fixed in this update",
)
async def announce_update_command(
    interaction: discord.Interaction,
    version: str,
    additions: str = "",
    improvements: str = "",
    fixes: str = "",
) -> None:

    await interaction.response.defer(
        ephemeral=True
    )

    if not version.strip() or len(version) > 30:
        await interaction.followup.send(
            "اكتب رقم إصدار صحيحًا (بحد أقصى 30 حرفًا).",
            ephemeral=True,
        )
        return

    if any(
        len(value) > 1000
        for value in (
            additions,
            improvements,
            fixes,
        )
    ):
        await interaction.followup.send(
            "كل قسم من تفاصيل التحديث يجب ألا يتجاوز 1000 حرف.",
            ephemeral=True,
        )
        return

    channel = await fetch_text_channel(
        ARCADE_NEWS_CHANNEL_ID
    )

    if (
        channel is None
        or channel.guild.id != interaction.guild.id
    ):
        await interaction.followup.send(
            "تعذر العثور على قناة أخبار MHN ARCADE.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=f"🚀 MHN ARCADE {version} — UPDATE",
        description=(
            "💜 صدر تحديث جديد! إليكم أبرز التغييرات والإضافات."
        ),
        color=PURPLE,
    )

    sections = (
        (
            "✨ الإضافات الجديدة | New Additions",
            additions,
        ),
        (
            "⚙️ التحسينات | Improvements",
            improvements,
        ),
        (
            "🛠️ الإصلاحات | Bug Fixes",
            fixes,
        ),
    )

    for title, content in sections:
        if content.strip():
            embed.add_field(
                name=title,
                value=content.strip(),
                inline=False,
            )

    if not embed.fields:
        embed.description = (
            "💜 صدر تحديث جديد لـ MHN ARCADE V3.\n"
            "A new MHN ARCADE V3 update is now available."
        )

    embed.set_footer(
        text=f"MHN ARCADE {version} • PLAY • COMPETE • WIN"
    )

    try:
        await channel.send(
            embed=embed
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "البوت ما عنده صلاحية إرسال الرسائل في قناة الأخبار.",
            ephemeral=True,
        )
        return

    except discord.HTTPException:
        logger.exception(
            "Could not publish update announcement."
        )

        await interaction.followup.send(
            "تعذر نشر إعلان التحديث بسبب خطأ من Discord.",
            ephemeral=True,
        )
        return

    await interaction.followup.send(
        f"✅ تم نشر إعلان MHN ARCADE {version}.",
        ephemeral=True,
    )


# ========================================================
# PING COMMAND
# ========================================================

@bot.tree.command(
    name="ping",
    description="Check MHN ARCADE V3 connection",
)
async def ping_command(
    interaction: discord.Interaction,
) -> None:

    latency = round(
        bot.latency * 1000
    )

    embed = build_embed(
        "💜 MHN ARCADE V3",
        (
            "نظام الأركيد يعمل بنجاح!\n\n"
            f"🏓 **Ping:** {latency} ms"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


# ========================================================
# GLOBAL COMMAND ERROR HANDLER
# ========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:

    logger.error(
        "Application command error: %s",
        error,
        exc_info=(
            type(error),
            error,
            error.__traceback__,
        ),
    )

    if isinstance(
        error,
        app_commands.MissingPermissions,
    ):
        message = (
            "❌ تحتاج صلاحية **Manage Server** لاستخدام هذا الأمر."
        )

    else:
        message = (
            "حدث خطأ أثناء تنفيذ الأمر. حاول مرة ثانية."
        )

    try:
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

    except discord.HTTPException:
        pass


# ========================================================
# START BOT
# ========================================================

if __name__ == "__main__":
    logger.info(
        "Starting MHN ARCADE V3..."
    )

    bot.run(TOKEN)
