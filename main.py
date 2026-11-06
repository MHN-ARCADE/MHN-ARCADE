"""
========================================================
MHN ARCADE V1
Main Bot Engine 💜
========================================================
"""

import os
import logging

import discord
from discord.ext import commands
from discord import app_commands

from database import (
    initialize_database,
    create_player,
    get_player,
    select_language,
    get_bot_message,
    save_bot_message,
    ensure_progress,
    get_player_card_data,
    get_achievement_count,
    unlock_achievement,
    get_all_time_leaderboard,
    get_season_leaderboard,
)


# ========================================================
# CONFIGURATION
# ========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing!")

ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910

PLAYER_CARDS_CHANNEL_ID = 1567719418862112809
LEADERBOARD_CHANNEL_ID = 1567720123106857142
ACHIEVEMENTS_CHANNEL_ID = 1567722630969303090

PURPLE = 0x7C3AED

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
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

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Game(
                name="MHN ARCADE V1 🎮"
            )
        )

    async def setup_hook(self):

        initialize_database()

        # Persistent button survives bot restarts.
        self.add_view(PlayerCardPanelView())

        synced = await self.tree.sync()

        logger.info(
            "Successfully synchronized %s slash commands.",
            len(synced)
        )


bot = MHNArcadeBot()


# ========================================================
# WELCOME EMBEDS
# ========================================================

def create_arabic_welcome():

    embed = discord.Embed(
        title="🎮 حياك في MHN ARCADE!",
        description=(
            "هنا جمعنا لك المتعة والتحدي بمكان واحد!\n"
            "العب، اختبر مهاراتك، وتحدا أصحابك في مجموعة "
            "ألعاب متنوعة، وكل لعبة لها جوها الخاص. 🕹️\n\n"
            "🏆 اجمع النقاط، نافس غيرك، وخل اسمك يتصدر بالقائمة!\n\n"
            "**PLAY • COMPETE • WIN**\n"
            "**YOUR GAME YOUR CHALLENGE.**\n\n"
            "💜 **MHN ARCADE V1 — LET THE FUN BEGIN!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **ملاحظة:** مع الوقت راح يرتفع الإصدار "
            "وتنضاف ألعاب ومميزات جديدة.\n"
            "هذا هو الإصدار الأول **V1**."
        ),
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V1 • PLAY • COMPETE • WIN"
    )

    return embed


def create_english_welcome():

    embed = discord.Embed(
        title="🎮 Welcome to MHN ARCADE!",
        description=(
            "We've brought fun and challenges together "
            "in one place!\n"
            "Play, test your skills, and challenge your "
            "friends across a variety of games. 🕹️\n\n"
            "🏆 Earn points, compete with others, "
            "and climb to the top of the leaderboard!\n\n"
            "**PLAY • COMPETE • WIN**\n"
            "**YOUR GAME YOUR CHALLENGE.**\n\n"
            "💜 **MHN ARCADE V1 — LET THE FUN BEGIN!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **Note:** New versions, games, and features "
            "will be added over time.\n"
            "This is the initial release: **V1**."
        ),
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V1 • PLAY • COMPETE • WIN"
    )

    return embed


# ========================================================
# WELCOME MESSAGE MANAGER
# ========================================================

async def ensure_welcome_message(
    guild: discord.Guild,
    message_key: str,
    channel_id: int,
    embed: discord.Embed
):

    saved_message = get_bot_message(
        guild.id,
        message_key
    )

    if saved_message:

        try:

            saved_channel = await bot.fetch_channel(
                int(saved_message["channel_id"])
            )

            if not hasattr(saved_channel, "fetch_message"):
                logger.error(
                    "Saved welcome destination cannot fetch messages: %s",
                    message_key
                )
                return False

            await saved_channel.fetch_message(
                int(saved_message["message_id"])
            )

            logger.info(
                "Welcome message already exists: %s",
                message_key
            )

            return True

        except discord.NotFound:

            logger.warning(
                "Saved welcome message was deleted: %s",
                message_key
            )

        except discord.Forbidden:

            logger.error(
                "Missing permission to read saved welcome message: %s",
                message_key
            )

            return False

        except discord.HTTPException as error:

            logger.error(
                "Could not verify saved welcome message: %s",
                error
            )

            return False

    channel = bot.get_channel(channel_id)

    if channel is None:

        try:

            channel = await bot.fetch_channel(channel_id)

        except discord.NotFound:

            logger.error(
                "Welcome channel does not exist: %s",
                channel_id
            )

            return False

        except discord.Forbidden:

            logger.error(
                "Missing permission to access welcome channel: %s",
                channel_id
            )

            return False

        except discord.HTTPException as error:

            logger.error(
                "Failed to fetch welcome channel: %s",
                error
            )

            return False

    if not isinstance(channel, discord.TextChannel):
        logger.error("Welcome destination is not a text channel.")
        return False

    if channel.guild.id != guild.id:
        return False

    try:

        message = await channel.send(embed=embed)

        save_bot_message(
            guild.id,
            message_key,
            channel.id,
            message.id
        )

        logger.info(
            "Welcome message sent: %s",
            message_key
        )

        return True

    except discord.Forbidden:

        logger.error(
            "Missing permission to send welcome message in %s",
            channel.name
        )

        return False

    except discord.HTTPException as error:

        logger.error(
            "Failed to send welcome message: %s",
            error
        )

        return False


async def initialize_welcome_messages_for_guild(guild):

    arabic_success = await ensure_welcome_message(
        guild=guild,
        message_key="welcome_ar",
        channel_id=ARABIC_ARCADE_CHANNEL_ID,
        embed=create_arabic_welcome()
    )

    english_success = await ensure_welcome_message(
        guild=guild,
        message_key="welcome_en",
        channel_id=ENGLISH_ARCADE_CHANNEL_ID,
        embed=create_english_welcome()
    )

    return arabic_success and english_success


async def initialize_welcome_messages():

    all_successful = True

    for guild in bot.guilds:

        success = await initialize_welcome_messages_for_guild(guild)

        if not success:
            all_successful = False

    return all_successful


# ========================================================
# PERSISTENT MESSAGE MANAGER
# ========================================================

async def ensure_saved_embed_message(
    guild,
    message_key,
    channel_id,
    embed,
    view=None
):

    saved = get_bot_message(
        guild.id,
        message_key
    )

    channel = bot.get_channel(channel_id)

    if channel is None:

        try:
            channel = await bot.fetch_channel(channel_id)

        except discord.HTTPException:

            logger.exception(
                "Could not fetch channel %s",
                channel_id
            )

            return False

    if not isinstance(channel, discord.TextChannel):
        logger.error("Invalid text channel: %s", channel_id)
        return False

    if channel.guild.id != guild.id:
        return False

    if saved:

        try:

            old_channel = await bot.fetch_channel(
                int(saved["channel_id"])
            )

            old_message = await old_channel.fetch_message(
                int(saved["message_id"])
            )

            if old_channel.id != channel.id:

                await old_message.delete()

            else:

                await old_message.edit(
                    embed=embed,
                    view=view
                )

                logger.info(
                    "Updated persistent message: %s",
                    message_key
                )

                return True

        except discord.NotFound:
            pass

        except discord.Forbidden:

            logger.error(
                "Missing permission for persistent message: %s",
                message_key
            )

            return False

        except discord.HTTPException:

            logger.exception(
                "Could not update persistent message: %s",
                message_key
            )

            return False

    try:

        message = await channel.send(
            embed=embed,
            view=view
        )

        save_bot_message(
            guild.id,
            message_key,
            channel.id,
            message.id
        )

        logger.info(
            "Created persistent message: %s",
            message_key
        )

        return True

    except discord.Forbidden:

        logger.error(
            "Missing permission to send persistent message: %s",
            message_key
        )

        return False

    except discord.HTTPException:

        logger.exception(
            "Could not create persistent message: %s",
            message_key
        )

        return False


# ========================================================
# ARCADE GUIDES
# ========================================================

def create_arabic_guide():

    embed = discord.Embed(
        title="📘 دليل MHN ARCADE",
        description=(
            "أهلًا بك في MHN ARCADE! 💜\n\n"
            "**🎮 كيف تبدأ؟**\n"
            "1. اختر لغتك باستخدام `/language`.\n"
            "2. استخدم القنوات المخصصة للألعاب.\n"
            "3. تابع بطاقتك وإحصائياتك في قناة بطاقات اللاعبين.\n"
            "4. نافس اللاعبين وتابع ترتيبك في لوحة المتصدرين.\n\n"
            "**🏆 نظام التقدم**\n"
            "• تبدأ من المستوى 0.\n"
            "• XP والتقدم مرتبطان بالألعاب.\n"
            "• الإنجازات تُسجل عند فتحها.\n\n"
            "**💜 ملاحظة**\n"
            "المزيد من الألعاب والأنظمة ستصل مع التحديثات القادمة.\n\n"
            "استخدم `/ping` للتأكد من اتصال البوت."
        ),
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V1 • PLAY • COMPETE • WIN"
    )

    return embed


def create_english_guide():

    embed = discord.Embed(
        title="📘 MHN ARCADE Guide",
        description=(
            "Welcome to MHN ARCADE! 💜\n\n"
            "**🎮 How to get started**\n"
            "1. Choose your language using `/language`.\n"
            "2. Use the designated arcade channels.\n"
            "3. Check your player card and statistics.\n"
            "4. Compete and follow your position on the leaderboard.\n\n"
            "**🏆 Progression**\n"
            "• Every player starts at Level 0.\n"
            "• XP and progression are tied to games.\n"
            "• Achievements are recorded when unlocked.\n\n"
            "**💜 Note**\n"
            "More games and features will arrive in future updates.\n\n"
            "Use `/ping` to check the bot connection."
        ),
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V1 • PLAY • COMPETE • WIN"
    )

    return embed


# ========================================================
# PLAYER RANK DISPLAY
# ========================================================

def get_rank_name(level):

    if level >= 300:
        return "GRANDMASTER"

    if level >= 175:
        return "MANAGER"

    if level >= 100:
        return "MASTER"

    if level >= 50:
        return "ELITE"

    if level >= 25:
        return "PRO"

    if level >= 10:
        return "APPRENTICE"

    return "ROOKIE"


# ========================================================
# PLAYER CARD EMBED
# ========================================================

def create_player_card_embed(guild, user, language):

    data = get_player_card_data(
        guild.id,
        user.id,
        language
    )

    if data is None:
        return None

    achievements = get_achievement_count(
        guild.id,
        user.id,
        language
    )

    games = data["games_played"]
    wins = data["wins"]

    win_rate = (
        (wins / games) * 100
        if games > 0
        else 0
    )

    if language == "ar":

        embed = discord.Embed(
            title="💜 بطاقة اللاعب",
            description=(
                f"**{data['username']}**\n"
                f"رتبة اللاعب: **{get_rank_name(data['level'])}**"
            ),
            color=PURPLE
        )

        embed.add_field(
            name="⭐ المستوى",
            value=f"Level {data['level']}",
            inline=True
        )

        embed.add_field(
            name="✨ XP",
            value=f"{data['xp']:,}",
            inline=True
        )

        embed.add_field(
            name="🏆 Prestige",
            value=str(data["prestige"]),
            inline=True
        )

        embed.add_field(
            name="🎮 المباريات",
            value=str(games),
            inline=True
        )

        embed.add_field(
            name="🥇 الانتصارات",
            value=str(wins),
            inline=True
        )

        embed.add_field(
            name="📊 نسبة الفوز",
            value=f"{win_rate:.1f}%",
            inline=True
        )

        embed.add_field(
            name="🔥 أفضل سلسلة",
            value=str(data["best_streak"]),
            inline=True
        )

        embed.add_field(
            name="🏅 الإنجازات",
            value=str(achievements),
            inline=True
        )

        embed.add_field(
            name="📈 إجمالي XP",
            value=f"{data['lifetime_xp']:,}",
            inline=True
        )

        embed.set_footer(
            text="MHN ARCADE V1 • PLAYER PROFILE"
        )

    else:

        embed = discord.Embed(
            title="💜 Player Card",
            description=(
                f"**{data['username']}**\n"
                f"Player Rank: **{get_rank_name(data['level'])}**"
            ),
            color=PURPLE
        )

        embed.add_field(
            name="⭐ Level",
            value=str(data["level"]),
            inline=True
        )

        embed.add_field(
            name="✨ XP",
            value=f"{data['xp']:,}",
            inline=True
        )

        embed.add_field(
            name="🏆 Prestige",
            value=str(data["prestige"]),
            inline=True
        )

        embed.add_field(
            name="🎮 Games Played",
            value=str(games),
            inline=True
        )

        embed.add_field(
            name="🥇 Wins",
            value=str(wins),
            inline=True
        )

        embed.add_field(
            name="📊 Win Rate",
            value=f"{win_rate:.1f}%",
            inline=True
        )

        embed.add_field(
            name="🔥 Best Streak",
            value=str(data["best_streak"]),
            inline=True
        )

        embed.add_field(
            name="🏅 Achievements",
            value=str(achievements),
            inline=True
        )

        embed.add_field(
            name="📈 Lifetime XP",
            value=f"{data['lifetime_xp']:,}",
            inline=True
        )

        embed.set_footer(
            text="MHN ARCADE V1 • PLAYER PROFILE"
        )

    return embed


# ========================================================
# PLAYER CARD PANEL BUTTON
# ========================================================

class PlayerCardPanelView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(
        label="عرض بطاقة اللاعب",
        emoji="🎮",
        style=discord.ButtonStyle.primary,
        custom_id="mhn_arcade:player_card"
    )
    async def show_card(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "Use this button inside the server.",
                ephemeral=True
            )

            return

        player = get_player(
            interaction.guild.id,
            interaction.user.id
        )

        if player is None:

            create_player(
                interaction.guild.id,
                interaction.user.id,
                interaction.user.name
            )

            player = get_player(
                interaction.guild.id,
                interaction.user.id
            )

        language = player["active_language"]

        if language not in ("ar", "en"):

            await interaction.response.send_message(
                "💜 اختر لغتك أولًا باستخدام `/language`.",
                ephemeral=True
            )

            return

        ensure_progress(
            interaction.guild.id,
            interaction.user.id,
            language
        )

        embed = create_player_card_embed(
            interaction.guild,
            interaction.user,
            language
        )

        if embed is None:

            await interaction.response.send_message(
                "Could not load your player card. Try again.",
                ephemeral=True
            )

            return

        channel = bot.get_channel(
            PLAYER_CARDS_CHANNEL_ID
        )

        if channel is None:

            try:

                channel = await bot.fetch_channel(
                    PLAYER_CARDS_CHANNEL_ID
                )

            except discord.HTTPException:

                await interaction.response.send_message(
                    "Player Cards channel is unavailable.",
                    ephemeral=True
                )

                return

        if not isinstance(channel, discord.TextChannel):

            await interaction.response.send_message(
                "Player Cards channel is not configured correctly.",
                ephemeral=True
            )

            return

        message_key = f"player_card:{interaction.user.id}"

        saved = get_bot_message(
            interaction.guild.id,
            message_key
        )

        if saved:

            try:

                old_channel = await bot.fetch_channel(
                    int(saved["channel_id"])
                )

                old_message = await old_channel.fetch_message(
                    int(saved["message_id"])
                )

                if old_channel.id != channel.id:

                    await old_message.delete()

                else:

                    await old_message.edit(
                        embed=embed
                    )

                    await interaction.response.send_message(
                        "💜 تم تحديث بطاقة لاعبك!",
                        ephemeral=True
                    )

                    return

            except discord.NotFound:
                pass

            except discord.Forbidden:

                await interaction.response.send_message(
                    "I cannot access your previous player card.",
                    ephemeral=True
                )

                return

            except discord.HTTPException:

                await interaction.response.send_message(
                    "Could not update your player card. Try again.",
                    ephemeral=True
                )

                return

        try:

            message = await channel.send(
                embed=embed
            )

            save_bot_message(
                interaction.guild.id,
                message_key,
                channel.id,
                message.id
            )

            await interaction.response.send_message(
                "💜 تم إنشاء بطاقة لاعبك في قناة بطاقات اللاعبين!",
                ephemeral=True
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "Could not create your player card. Check bot permissions.",
                ephemeral=True
            )


# ========================================================
# LEADERBOARD EMBEDS
# ========================================================

def create_leaderboard_embed(
    guild,
    language,
    seasonal=False
):

    if seasonal:

        season, rows = get_season_leaderboard(
            guild.id,
            language,
            10
        )

        if language == "ar":
            title = "🏆 المتصدرون العرب • الموسم"
            empty = "لا يوجد موسم نشط حاليًا."
            no_players = "لا يوجد لاعبون في ترتيب هذا الموسم بعد."

        else:
            title = "🏆 English Leaderboard • Season"
            empty = "There is no active season right now."
            no_players = "No players ranked in this season yet."

        if season is None:

            description = empty

        elif not rows:

            description = (
                f"**{season['name']}**\n\n"
                f"{no_players}"
            )

        else:

            description = f"**{season['name']}**\n\n"

            for index, row in enumerate(rows, start=1):

                description += (
                    f"**{index}.** {row['username']} "
                    f"— {row['xp']:,} XP\n"
                )

    else:

        rows = get_all_time_leaderboard(
            guild.id,
            language,
            10
        )

        if language == "ar":
            title = "🏆 المتصدرون العرب • إجمالي"
            empty = "لا يوجد لاعبون في الترتيب حتى الآن."

        else:
            title = "🏆 English Leaderboard • All Time"
            empty = "No players on the leaderboard yet."

        if not rows:

            description = empty

        else:

            description = ""

            for index, row in enumerate(rows, start=1):

                description += (
                    f"**{index}.** {row['username']} "
                    f"— Level {row['level']} "
                    f"• {row['xp']:,} XP\n"
                )

    embed = discord.Embed(
        title=title,
        description=description,
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V1 • TOP 10"
    )

    return embed


async def refresh_leaderboard(guild):

    embeds = [
        create_leaderboard_embed(guild, "ar", False),
        create_leaderboard_embed(guild, "ar", True),
        create_leaderboard_embed(guild, "en", False),
        create_leaderboard_embed(guild, "en", True),
    ]

    saved = get_bot_message(
        guild.id,
        "leaderboard_panel"
    )

    channel = bot.get_channel(
        LEADERBOARD_CHANNEL_ID
    )

    if channel is None:

        try:

            channel = await bot.fetch_channel(
                LEADERBOARD_CHANNEL_ID
            )

        except discord.HTTPException:

            logger.exception(
                "Leaderboard channel unavailable."
            )

            return False

    if not isinstance(channel, discord.TextChannel):
        return False

    if saved:

        try:

            old_channel = await bot.fetch_channel(
                int(saved["channel_id"])
            )

            old_message = await old_channel.fetch_message(
                int(saved["message_id"])
            )

            if old_channel.id != channel.id:

                await old_message.delete()

            else:

                await old_message.edit(
                    embeds=embeds
                )

                logger.info("Leaderboard updated.")
                return True

        except discord.NotFound:
            pass

        except discord.Forbidden:

            logger.error(
                "Missing permission to update leaderboard."
            )

            return False

        except discord.HTTPException:

            logger.exception(
                "Could not update leaderboard."
            )

            return False

    try:

        message = await channel.send(
            embeds=embeds
        )

        save_bot_message(
            guild.id,
            "leaderboard_panel",
            channel.id,
            message.id
        )

        logger.info("Leaderboard created.")
        return True

    except discord.HTTPException:

        logger.exception(
            "Could not create leaderboard."
        )

        return False


# ========================================================
# ACHIEVEMENT ANNOUNCEMENTS
# ========================================================

async def announce_achievement(
    guild,
    user,
    language,
    achievement_key,
    title_ar,
    title_en,
    description_ar,
    description_en
):

    if language not in ("ar", "en"):
        return False

    newly_unlocked = unlock_achievement(
        guild.id,
        user.id,
        language,
        achievement_key
    )

    if not newly_unlocked:
        return False

    channel = bot.get_channel(
        ACHIEVEMENTS_CHANNEL_ID
    )

    if channel is None:

        try:

            channel = await bot.fetch_channel(
                ACHIEVEMENTS_CHANNEL_ID
            )

        except discord.HTTPException:

            logger.exception(
                "Achievements channel unavailable."
            )

            return False

    if not isinstance(channel, discord.TextChannel):
        return False

    if language == "ar":

        title = f"🏅 إنجاز جديد: {title_ar}"

        description = (
            f"🎉 اللاعب {user.mention} فتح إنجازًا جديدًا!\n\n"
            f"{description_ar}"
        )

    else:

        title = f"🏅 New Achievement: {title_en}"

        description = (
            f"🎉 {user.mention} unlocked a new achievement!\n\n"
            f"{description_en}"
        )

    embed = discord.Embed(
        title=title,
        description=description,
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V1 • ACHIEVEMENT UNLOCKED"
    )

    try:

        await channel.send(embed=embed)
        return True

    except discord.HTTPException:

        logger.exception(
            "Achievement announcement failed."
        )

        return False


# ========================================================
# INITIALIZE ARCADE SYSTEMS
# ========================================================

async def initialize_arcade_systems(guild):

    await ensure_saved_embed_message(
        guild,
        "guide_ar",
        ARABIC_ARCADE_CHANNEL_ID,
        create_arabic_guide()
    )

    await ensure_saved_embed_message(
        guild,
        "guide_en",
        ENGLISH_ARCADE_CHANNEL_ID,
        create_english_guide()
    )

    panel_embed = discord.Embed(
        title="🎮 بطاقات اللاعبين | Player Cards",
        description=(
            "اضغط الزر بالأسفل لإنشاء بطاقة لاعبك أو تحديثها.\n"
            "Your player card will be created or updated here.\n\n"
            "💜 بطاقة واحدة لكل لاعب، بدون تكرار."
        ),
        color=PURPLE
    )

    await ensure_saved_embed_message(
        guild,
        "player_card_panel",
        PLAYER_CARDS_CHANNEL_ID,
        panel_embed,
        view=PlayerCardPanelView()
    )

    await refresh_leaderboard(guild)

    logger.info(
        "Arcade systems initialized for guild: %s",
        guild.name
    )


# ========================================================
# BOT READY
# ========================================================

@bot.event
async def on_ready():

    logger.info("=" * 45)
    logger.info("💜 MHN ARCADE V1")
    logger.info("Logged in as: %s", bot.user)
    logger.info("Bot ID: %s", bot.user.id)
    logger.info("Servers: %s", len(bot.guilds))
    logger.info("Status: ONLINE")
    logger.info("=" * 45)

    welcome_success = await initialize_welcome_messages()

    if welcome_success:
        logger.info("Welcome messages verified successfully.")
    else:
        logger.warning(
            "Some welcome messages could not be verified."
        )

    for guild in bot.guilds:

        try:

            await initialize_arcade_systems(guild)

        except Exception:

            logger.exception(
                "Failed to initialize arcade systems for %s",
                guild.name
            )


# ========================================================
# AUTOMATIC PLAYER REGISTRATION
# ========================================================

@bot.event
async def on_member_join(member: discord.Member):

    if member.bot:
        return

    create_player(
        guild_id=member.guild.id,
        user_id=member.id,
        username=member.name
    )

    logger.info(
        "New player registered: %s (%s)",
        member.name,
        member.id
    )


# ========================================================
# PING COMMAND
# ========================================================

@bot.tree.command(
    name="ping",
    description="Check MHN ARCADE connection"
)
async def ping(interaction: discord.Interaction):

    latency = round(
        bot.latency * 1000
    )

    embed = discord.Embed(
        title="💜 MHN ARCADE V1",
        description=(
            "The arcade system is online!\n\n"
            f"🏓 **Ping:** {latency} ms"
        ),
        color=PURPLE
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ========================================================
# LANGUAGE SWITCH CONFIRMATION
# ========================================================

class LanguageConfirmationView(discord.ui.View):

    def __init__(
        self,
        member_id: int,
        guild_id: int,
        username: str,
        language: str
    ):

        super().__init__(timeout=120)

        self.member_id = member_id
        self.guild_id = guild_id
        self.username = username
        self.language = language

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        if interaction.user.id != self.member_id:

            await interaction.response.send_message(
                "❌ This confirmation belongs to another player.",
                ephemeral=True
            )

            return False

        return True

    @discord.ui.button(
        label="Confirm Reset",
        style=discord.ButtonStyle.danger,
        emoji="🔄"
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        switched, language = select_language(
            guild_id=self.guild_id,
            user_id=self.member_id,
            username=self.username,
            language=self.language
        )

        for item in self.children:
            item.disabled = True

        if language == "ar":

            title = "💜 تم تغيير اللغة"

            description = (
                "تم تغيير لغتك إلى **العربية** بنجاح.\n\n"
                "🎮 يبدأ تقدمك الجديد من المستوى 0 وبدون XP."
            )

        else:

            title = "💜 Language Updated"

            description = (
                "Your language is now **English**.\n\n"
                "🎮 Your new progress starts at Level 0 with 0 XP."
            )

        embed = discord.Embed(
            title=title,
            description=description,
            color=PURPLE
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.success,
        emoji="✖️"
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                "💜 Language change cancelled. "
                "Your progress remains unchanged."
            ),
            embed=None,
            view=self
        )

    async def on_timeout(self):

        for item in self.children:
            item.disabled = True


# ========================================================
# LANGUAGE COMMAND
# ========================================================

@bot.tree.command(
    name="language",
    description="Choose your MHN ARCADE language"
)
@app_commands.describe(
    language="Choose Arabic or English"
)
@app_commands.choices(
    language=[
        app_commands.Choice(
            name="العربية",
            value="ar"
        ),
        app_commands.Choice(
            name="English",
            value="en"
        )
    ]
)
async def language(
    interaction: discord.Interaction,
    language: app_commands.Choice[str]
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "This command can only be used inside the server.",
            ephemeral=True
        )

        return

    selected_language = language.value

    player = get_player(
        interaction.guild.id,
        interaction.user.id
    )

    if player is None:

        create_player(
            interaction.guild.id,
            interaction.user.id,
            interaction.user.name
        )

        player = get_player(
            interaction.guild.id,
            interaction.user.id
        )

    current_language = player["active_language"]

    if current_language == selected_language:

        await interaction.response.send_message(
            "💜 You are already using this language.",
            ephemeral=True
        )

        return

    if current_language is None:

        select_language(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            username=interaction.user.name,
            language=selected_language
        )

        if selected_language == "ar":

            title = "💜 تم اختيار اللغة"

            description = (
                "تم اختيار اللغة العربية بنجاح!\n\n"
                "🎮 رحلتك تبدأ الآن من المستوى 0."
            )

        else:

            title = "💜 Language Selected"

            description = (
                "Your arcade language is now **English**!\n\n"
                "🎮 Your journey starts at Level 0."
            )

        embed = discord.Embed(
            title=title,
            description=description,
            color=PURPLE
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        return

    if selected_language == "ar":

        title = "⚠️ تأكيد تغيير اللغة"

        description = (
            "هل أنت متأكد من تغيير اللغة إلى العربية؟\n\n"
            "🔴 **تنبيه:** تغيير اللغة سيؤدي إلى تصفير "
            "تقدمك في مساري العربية والإنجليزية، "
            "بما في ذلك المستوى وXP والإحصائيات والإنجازات.\n\n"
            "سيتم أيضًا تصفير إحصائيات المواسم النشطة فقط.\n"
            "أما المواسم المنتهية وألقابك الخاصة فستبقى محفوظة.\n\n"
            "لن يتم التغيير إلا بعد تأكيدك."
        )

    else:

        title = "⚠️ Confirm Language Change"

        description = (
            "Are you sure you want to switch to English?\n\n"
            "🔴 **Warning:** Switching languages will reset "
            "your progress in both Arabic and English tracks, "
            "including levels, XP, statistics, and achievements.\n\n"
            "Your active season statistics will also reset.\n"
            "Ended season archives and special titles will remain preserved.\n\n"
            "Nothing will change until you confirm."
        )

    embed = discord.Embed(
        title=title,
        description=description,
        color=0xDC2626
    )

    view = LanguageConfirmationView(
        member_id=interaction.user.id,
        guild_id=interaction.guild.id,
        username=interaction.user.name,
        language=selected_language
    )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )


# ========================================================
# GLOBAL PREFIX COMMAND ERROR HANDLER
# ========================================================

@bot.event
async def on_command_error(ctx, error):

    logger.error(
        "Command error: %s",
        error,
        exc_info=error
    )


# ========================================================
# START BOT
# ========================================================

if __name__ == "__main__":

    logger.info("Starting MHN ARCADE V1...")

    bot.run(TOKEN)
