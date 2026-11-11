
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
- Automatic arcade message cleanup

Message cleanup:
- Member messages in Arabic and English arcade channels:
  Delete 60 minutes after sending.
- Finished game messages:
  Shared 5-minute deletion scheduler for V3 game views.
- Bot messages and persistent menus are exempt from
  the automatic 60-minute member-message cleanup.

Environment:
    DISCORD_TOKEN
========================================================
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

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

ARCADE_CHANNEL_IDS = {
    ARABIC_ARCADE_CHANNEL_ID,
    ENGLISH_ARCADE_CHANNEL_ID,
}

PLAYER_CARDS_CHANNEL_ID = 1567719418862112809
ARCADE_NEWS_CHANNEL_ID = 1568381560279933049

MEMBER_MESSAGE_DELETE_SECONDS = 60 * 60
FINISHED_GAME_DELETE_SECONDS = 5 * 60

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
intents.message_content = True


# ========================================================
# ARCADE MESSAGE CLEANUP
# ========================================================

class ArcadeMessageCleanup:
    """
    Centralized message cleanup manager.

    Member messages:
        Deleted 60 minutes after creation.

    Finished game messages:
        Can be scheduled for deletion after 5 minutes
        through schedule_game_message().

    Only the Arabic and English arcade channels are managed.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self._tasks: dict[int, asyncio.Task] = {}
        self._initialized = False

    # ----------------------------------------------------
    # CHANNEL VALIDATION
    # ----------------------------------------------------

    @staticmethod
    def is_arcade_channel(channel_id: int) -> bool:
        return channel_id in ARCADE_CHANNEL_IDS

    # ----------------------------------------------------
    # MESSAGE DELETION
    # ----------------------------------------------------

    async def delete_message(
        self,
        message: discord.Message,
        reason: str = "Scheduled arcade cleanup",
    ) -> bool:

        if not self.is_arcade_channel(message.channel.id):
            return False

        try:
            await message.delete()

            logger.info(
                "Deleted arcade message %s | Channel: %s | Reason: %s",
                message.id,
                message.channel.id,
                reason,
            )

            return True

        except discord.NotFound:
            return True

        except discord.Forbidden:
            logger.error(
                "Missing permission to delete message %s.",
                message.id,
            )

        except discord.HTTPException:
            logger.exception(
                "Failed to delete arcade message %s.",
                message.id,
            )

        return False

    # ----------------------------------------------------
    # SCHEDULED DELETION
    # ----------------------------------------------------

    def schedule_message_delete(
        self,
        message: discord.Message,
        delay_seconds: int,
        reason: str = "Scheduled arcade cleanup",
    ) -> None:
        """
        Schedule one message for deletion.

        If the same message already has a scheduled task,
        the previous task is replaced.
        """

        if not self.is_arcade_channel(message.channel.id):
            return

        if message.id in self._tasks:
            previous_task = self._tasks.pop(message.id)

            if not previous_task.done():
                previous_task.cancel()

        task = asyncio.create_task(
            self._delete_after_delay(
                message=message,
                delay_seconds=delay_seconds,
                reason=reason,
            )
        )

        self._tasks[message.id] = task

    async def _delete_after_delay(
        self,
        message: discord.Message,
        delay_seconds: int,
        reason: str,
    ) -> None:

        message_id = message.id
        current_task = asyncio.current_task()

        try:
            await asyncio.sleep(
                max(0, delay_seconds)
            )

            await self.delete_message(
                message,
                reason=reason,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Unexpected cleanup error for message %s.",
                message_id,
            )

        finally:
            if self._tasks.get(message_id) is current_task:
                self._tasks.pop(message_id, None)

    # ----------------------------------------------------
    # MEMBER MESSAGE CLEANUP
    # ----------------------------------------------------

    def schedule_member_message(
        self,
        message: discord.Message,
    ) -> None:
        """
        Schedule a member message for deletion exactly
        60 minutes after its creation time.
        """

        if not self.is_arcade_channel(message.channel.id):
            return

        if message.author.bot or message.webhook_id is not None:
            return

        delete_at = (
            message.created_at
            + timedelta(
                seconds=MEMBER_MESSAGE_DELETE_SECONDS
            )
        )

        now = datetime.now(timezone.utc)

        remaining_seconds = (
            delete_at - now
        ).total_seconds()

        self.schedule_message_delete(
            message=message,
            delay_seconds=max(
                0,
                int(remaining_seconds),
            ),
            reason="Member message reached 60-minute limit",
        )

    # ----------------------------------------------------
    # FINISHED GAME MESSAGE CLEANUP
    # ----------------------------------------------------

    def schedule_game_message(
        self,
        message: discord.Message,
    ) -> None:
        """
        Schedule a finished game message for deletion
        5 minutes after the final result is displayed.

        Active game messages must never use this method
        until the game has actually ended.
        """

        self.schedule_message_delete(
            message=message,
            delay_seconds=FINISHED_GAME_DELETE_SECONDS,
            reason="Finished game message reached 5-minute limit",
        )

    # ----------------------------------------------------
    # MEMBER MESSAGE EVENT
    # ----------------------------------------------------

    async def on_message(
        self,
        message: discord.Message,
    ) -> None:

        if not self.is_arcade_channel(message.channel.id):
            return

        if message.author.bot or message.webhook_id is not None:
            return

        self.schedule_member_message(message)

    # ----------------------------------------------------
    # STARTUP HISTORY SCAN
    # ----------------------------------------------------

    async def initialize(self) -> None:
        """
        Scan both arcade channels after startup.

        Old member messages:
            Delete immediately if already 60 minutes old.

        Recent member messages:
            Resume their remaining deletion time.

        Bot messages:
            Always ignored.
        """

        if self._initialized:
            return

        self._initialized = True

        logger.info(
            "Initializing arcade message cleanup."
        )

        for channel_id in ARCADE_CHANNEL_IDS:
            channel = self.bot.get_channel(channel_id)

            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(
                        channel_id
                    )

                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    logger.exception(
                        "Could not access arcade channel %s.",
                        channel_id,
                    )
                    continue

            if not isinstance(channel, discord.TextChannel):
                logger.error(
                    "Arcade channel %s is not a text channel.",
                    channel_id,
                )
                continue

            logger.info(
                "Scanning arcade channel: %s",
                channel.name,
            )

            try:
                async for message in channel.history(
                    limit=None,
                    oldest_first=True,
                ):

                    if message.author.bot:
                        continue

                    if message.webhook_id is not None:
                        continue

                    delete_at = (
                        message.created_at
                        + timedelta(
                            seconds=MEMBER_MESSAGE_DELETE_SECONDS
                        )
                    )

                    remaining_seconds = (
                        delete_at
                        - datetime.now(timezone.utc)
                    ).total_seconds()

                    if remaining_seconds <= 0:
                        await self.delete_message(
                            message,
                            reason="Startup scan: message older than 60 minutes",
                        )

                    else:
                        self.schedule_message_delete(
                            message=message,
                            delay_seconds=int(
                                remaining_seconds
                            ),
                            reason="Member message reached 60-minute limit",
                        )

            except discord.Forbidden:
                logger.error(
                    "Missing permission to read history in channel %s.",
                    channel_id,
                )

            except discord.HTTPException:
                logger.exception(
                    "Could not scan arcade channel %s.",
                    channel_id,
                )

        logger.info(
            "Arcade message cleanup initialization completed."
        )

    # ----------------------------------------------------
    # SHUTDOWN
    # ----------------------------------------------------

    def shutdown(self) -> None:
        for task in self._tasks.values():
            if not task.done():
                task.cancel()

        self._tasks.clear()

        logger.info(
            "Arcade message cleanup tasks stopped."
        )


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

        self.message_cleanup = ArcadeMessageCleanup(self)

    async def setup_hook(self) -> None:
        # Initialize the existing database and V3 profiles.
        initialize_database()
        initialize_player_profiles()

        # Register the member-message cleanup listener.
        self.add_listener(
            self.message_cleanup.on_message,
            "on_message",
        )

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

        self.add_view(
            V3PlayerCardPanelView()
        )

        synced = await self.tree.sync()

        logger.info(
            "Successfully synchronized %s V3 slash commands.",
            len(synced),
        )

    async def close(self) -> None:
        self.message_cleanup.shutdown()
        await super().close()


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

    # Initialize cleanup once, including after reconnects.
    await bot.message_cleanup.initialize()

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
