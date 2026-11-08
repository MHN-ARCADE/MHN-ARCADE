"""
========================================================
MHN ARCADE V2.0
Main Bot Engine 💜
========================================================

Features:
- Arabic and English welcome messages
- Player registration
- Language selection
- Player cards
- Character selection
- Arcade games extension
- XP and level progression
- Wallet and bank
- All-time and seasonal leaderboards
- Achievement announcements
- Persistent Discord messages

Environment:
    DISCORD_TOKEN

Files:
    main.py
    database.py
    games.py
    characters.py
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
    get_wallet,
    deposit_coins,
    withdraw_coins,
    get_selected_character,
    select_character,
    xp_required_for_next_level,
)

from characters import (
    CHARACTERS,
    CATEGORY_ANIME,
    CATEGORY_NETFLIX,
    get_character,
    get_characters_by_category,
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
ARCADE_NEWS_CHANNEL_ID = 1568381560279933049

PURPLE = 0x7C3AED
VERSION = "V2.0"

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
                name="MHN ARCADE V2.0 🎮"
            )
        )

    async def setup_hook(self):

        initialize_database()

        # Persistent player card button.
        self.add_view(PlayerCardPanelView())

        # Load the arcade games engine.
        await self.load_extension("games")
        # Load the MHN ARCADE V3 engine.
        await self.load_extension("v3_discord")
        synced = await self.tree.sync()

        logger.info(
            "Successfully synchronized %s slash commands.",
            len(synced)
        )


bot = MHNArcadeBot()


# ========================================================
# GENERAL HELPERS
# ========================================================

def build_embed(title, description, color=PURPLE):

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.set_footer(
        text=f"MHN ARCADE {VERSION} • PLAY • COMPETE • WIN"
    )

    return embed


def get_language(guild_id, user_id):

    player = get_player(guild_id, user_id)

    if player and player["active_language"] in ("ar", "en"):
        return player["active_language"]

    return None


def get_rank_name(level):

    if level >= 500:
        return "MYTHIC"

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


async def fetch_text_channel(channel_id):

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.HTTPException:
            logger.exception("Could not fetch channel %s", channel_id)
            return None

    if not isinstance(channel, discord.TextChannel):
        return None

    return channel


# ========================================================
# WELCOME EMBEDS
# ========================================================

def create_arabic_welcome():

    embed = discord.Embed(
        title="🎮 حياك في MHN ARCADE!",
        description=(
            "مرحبًا بك في عالم MHN ARCADE! 💜\n\n"
            "هنا تبدأ رحلتك في الألعاب والتحديات.\n"
            "اختبر مهاراتك، نافس أصحابك، واجمع XP والعملات "
            "وارفع مستواك حتى تصل إلى القمة!\n\n"
            "🏆 **نظام مستويات وتقدم**\n"
            "🪙 **محفظة وبنك ومكافآت**\n"
            "🎭 **شخصيات أنمي ونتفلكس**\n"
            "🎮 **مجموعة ألعاب متنوعة**\n"
            "📊 **بطاقات لاعبين ولوحات متصدرين**\n\n"
            "**PLAY • COMPETE • WIN**\n"
            "**YOUR GAME YOUR CHALLENGE.**\n\n"
            "💜 **MHN ARCADE V2.0 — THE NEXT LEVEL.**"
        ),
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V2.0 • PLAY • COMPETE • WIN"
    )

    return embed


def create_english_welcome():

    embed = discord.Embed(
        title="🎮 Welcome to MHN ARCADE!",
        description=(
            "Welcome to the world of MHN ARCADE! 💜\n\n"
            "Your journey through games and challenges starts here.\n"
            "Test your skills, compete with friends, earn XP and coins, "
            "and climb your way to the top!\n\n"
            "🏆 **Level and progression system**\n"
            "🪙 **Wallet, bank and rewards**\n"
            "🎭 **Anime and Netflix characters**\n"
            "🎮 **A variety of games**\n"
            "📊 **Player cards and leaderboards**\n\n"
            "**PLAY • COMPETE • WIN**\n"
            "**YOUR GAME YOUR CHALLENGE.**\n\n"
            "💜 **MHN ARCADE V2.0 — THE NEXT LEVEL.**"
        ),
        color=PURPLE
    )

    embed.set_footer(
        text="MHN ARCADE V2.0 • PLAY • COMPETE • WIN"
    )

    return embed


# ========================================================
# SAVED MESSAGE MANAGER
# ========================================================

async def ensure_saved_embed_message(
    guild,
    message_key,
    channel_id,
    embed,
    view=None
):

    channel = await fetch_text_channel(channel_id)

    if channel is None:
        logger.error("Invalid destination channel: %s", channel_id)
        return False

    if channel.guild.id != guild.id:
        return False

    saved = get_bot_message(guild.id, message_key)

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
                    view=view
                )

                logger.info("Updated saved message: %s", message_key)
                return True

            await old_message.delete()

        except discord.NotFound:
            logger.warning("Saved message missing: %s", message_key)

        except discord.Forbidden:
            logger.error("No permission to update: %s", message_key)
            return False

        except discord.HTTPException:
            logger.exception("Could not update: %s", message_key)
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

        logger.info("Created saved message: %s", message_key)
        return True

    except discord.HTTPException:
        logger.exception("Could not create message: %s", message_key)
        return False


async def initialize_welcome_messages_for_guild(guild):

    arabic = await ensure_saved_embed_message(
        guild,
        "welcome_ar",
        ARABIC_ARCADE_CHANNEL_ID,
        create_arabic_welcome()
    )

    english = await ensure_saved_embed_message(
        guild,
        "welcome_en",
        ENGLISH_ARCADE_CHANNEL_ID,
        create_english_welcome()
    )

    return arabic and english


async def initialize_welcome_messages():

    success = True

    for guild in bot.guilds:

        result = await initialize_welcome_messages_for_guild(guild)

        if not result:
            success = False

    return success


# ========================================================
# ARCADE GUIDES
# ========================================================

def create_arabic_guide():

    return build_embed(
        "📘 دليل MHN ARCADE V2.0",
        (
            "أهلًا بك في MHN ARCADE! 💜\n\n"
            "**🎮 البداية**\n"
            "• استخدم `/language` لاختيار لغتك.\n"
            "• استخدم `/arcade` لفتح قائمة الألعاب.\n"
            "• استخدم `/character` لاختيار شخصيتك.\n\n"
            "**🏆 التقدم**\n"
            "• اجمع XP وارفع مستواك.\n"
            "• اربح العملات من الألعاب.\n"
            "• تابع إحصائياتك باستخدام `/arcade_stats`.\n\n"
            "**🪙 الاقتصاد**\n"
            "• `/wallet` لعرض رصيدك.\n"
            "• `/deposit` لإيداع العملات في البنك.\n"
            "• `/withdraw` لسحب العملات من البنك.\n\n"
            "**📊 بطاقة اللاعب**\n"
            "استخدم زر بطاقة اللاعب في القناة المخصصة.\n\n"
            "**💜 استمتع باللعب والتحدي!**"
        )
    )


def create_english_guide():

    return build_embed(
        "📘 MHN ARCADE V2.0 Guide",
        (
            "Welcome to MHN ARCADE! 💜\n\n"
            "**🎮 Getting Started**\n"
            "• Use `/language` to choose your language.\n"
            "• Use `/arcade` to open the games menu.\n"
            "• Use `/character` to select your character.\n\n"
            "**🏆 Progression**\n"
            "• Earn XP and level up.\n"
            "• Win coins through games.\n"
            "• Check your stats using `/arcade_stats`.\n\n"
            "**🪙 Economy**\n"
            "• `/wallet` to view your balance.\n"
            "• `/deposit` to deposit coins.\n"
            "• `/withdraw` to withdraw coins.\n\n"
            "**📊 Player Card**\n"
            "Use the player card button in the designated channel.\n\n"
            "**💜 Play • Compete • Win!**"
        )
    )


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

    wallet = get_wallet(guild.id, user.id)

    selected = get_selected_character(
        guild.id,
        user.id
    )

    character = None

    if selected:
        character = get_character(selected["character_id"])

    games = data["games_played"]
    wins = data["wins"]

    win_rate = (
        (wins / games) * 100
        if games > 0
        else 0
    )

    next_level_xp = xp_required_for_next_level(data["level"])

    progress_bar_length = 10

    filled = min(
        progress_bar_length,
        int(
            (data["xp"] / max(1, next_level_xp))
            * progress_bar_length
        )
    )

    progress_bar = (
        "🟪" * filled
        + "⬛" * (progress_bar_length - filled)
    )

    character_name = (
        character["name_ar"]
        if character and language == "ar"
        else character["name"]
        if character
        else ("لم يتم اختيار شخصية" if language == "ar" else "No character selected")
    )

    if language == "ar":

        embed = discord.Embed(
            title="💜 بطاقة اللاعب",
            description=(
                f"**{data['username']}**\n"
                f"الرتبة: **{get_rank_name(data['level'])}**\n"
                f"الشخصية: **{character_name}**"
            ),
            color=PURPLE
        )

        embed.add_field(
            name="⭐ المستوى",
            value=str(data["level"]),
            inline=True
        )

        embed.add_field(
            name="✨ XP",
            value=f"{data['xp']:,} / {next_level_xp:,}",
            inline=True
        )

        embed.add_field(
            name="🏆 Prestige",
            value=str(data["prestige"]),
            inline=True
        )

        embed.add_field(
            name="📈 التقدم",
            value=progress_bar,
            inline=False
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
            name="🪙 المحفظة",
            value=f"{wallet['coins']:,}",
            inline=True
        )

        embed.add_field(
            name="🏦 البنك",
            value=f"{wallet['bank']:,}",
            inline=True
        )

        embed.add_field(
            name="📚 إجمالي XP",
            value=f"{data['lifetime_xp']:,}",
            inline=True
        )

    else:

        embed = discord.Embed(
            title="💜 Player Card",
            description=(
                f"**{data['username']}**\n"
                f"Rank: **{get_rank_name(data['level'])}**\n"
                f"Character: **{character_name}**"
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
            value=f"{data['xp']:,} / {next_level_xp:,}",
            inline=True
        )

        embed.add_field(
            name="🏆 Prestige",
            value=str(data["prestige"]),
            inline=True
        )

        embed.add_field(
            name="📈 Progress",
            value=progress_bar,
            inline=False
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
            name="🪙 Wallet",
            value=f"{wallet['coins']:,}",
            inline=True
        )

        embed.add_field(
            name="🏦 Bank",
            value=f"{wallet['bank']:,}",
            inline=True
        )

        embed.add_field(
            name="📚 Lifetime XP",
            value=f"{data['lifetime_xp']:,}",
            inline=True
        )

    if character and character.get("image_url"):
        embed.set_thumbnail(url=character["image_url"])

    embed.set_footer(
        text="MHN ARCADE V2.0 • PLAYER PROFILE"
    )

    return embed


# ========================================================
# PLAYER CARD PANEL
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

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        player = get_player(guild_id, user_id)

        if player is None:

            create_player(
                guild_id,
                user_id,
                interaction.user.name
            )

            player = get_player(guild_id, user_id)

        language = player["active_language"]

        if language not in ("ar", "en"):
            await interaction.response.send_message(
                "💜 اختر لغتك أولًا باستخدام `/language`.",
                ephemeral=True
            )
            return

        ensure_progress(
            guild_id,
            user_id,
            language
        )

        embed = create_player_card_embed(
            interaction.guild,
            interaction.user,
            language
        )

        if embed is None:
            await interaction.response.send_message(
                "Could not load your player card.",
                ephemeral=True
            )
            return

        channel = await fetch_text_channel(
            PLAYER_CARDS_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "Player Cards channel is unavailable.",
                ephemeral=True
            )
            return

        message_key = f"player_card:{user_id}"

        saved = get_bot_message(
            guild_id,
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

                if old_channel.id == channel.id:

                    await old_message.edit(embed=embed)

                    await interaction.response.send_message(
                        "💜 تم تحديث بطاقة لاعبك!",
                        ephemeral=True
                    )
                    return

                await old_message.delete()

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
                    "Could not update your player card.",
                    ephemeral=True
                )
                return

        try:

            message = await channel.send(embed=embed)

            save_bot_message(
                guild_id,
                message_key,
                channel.id,
                message.id
            )

            await interaction.response.send_message(
                "💜 تم إنشاء بطاقة لاعبك!",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "Could not create your player card.",
                ephemeral=True
            )


# ========================================================
# CHARACTER SELECT MENU
# ========================================================

class CharacterSelect(discord.ui.Select):

    def __init__(self, player_id, guild_id, category, language):

        self.player_id = player_id
        self.guild_id = guild_id
        self.category = category
        self.language = language

        characters = get_characters_by_category(category)

        options = []

        for character in characters:

            label = (
                character["name_ar"]
                if language == "ar"
                else character["name"]
            )

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=character["id"],
                    description=character["series"][:100]
                )
            )

        placeholder = (
            "اختر شخصية"
            if language == "ar"
            else "Choose your character"
        )

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "هذه القائمة ليست لك.",
                ephemeral=True
            )
            return

        character_id = self.values[0]
        character = get_character(character_id)

        if character is None:
            await interaction.response.send_message(
                "Character not found.",
                ephemeral=True
            )
            return

        select_character(
            self.guild_id,
            self.player_id,
            character_id
        )

        if self.language == "ar":

            embed = build_embed(
                "🎭 تم اختيار الشخصية!",
                (
                    f"اخترت شخصية **{character['name_ar']}** بنجاح!\n"
                    f"العمل: **{character['series']}**\n\n"
                    "ستظهر شخصيتك في بطاقة اللاعب."
                )
            )

        else:

            embed = build_embed(
                "🎭 Character Selected!",
                (
                    f"You selected **{character['name']}**!\n"
                    f"Series: **{character['series']}**\n\n"
                    "Your character will appear on your player card."
                )
            )

        if character.get("image_url"):
            embed.set_thumbnail(url=character["image_url"])

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )


class CharacterSelectView(discord.ui.View):

    def __init__(self, player_id, guild_id, category, language):

        super().__init__(timeout=120)

        self.add_item(
            CharacterSelect(
                player_id,
                guild_id,
                category,
                language
            )
        )


class CharacterCategoryButton(discord.ui.Button):

    def __init__(self, player_id, guild_id, category, language):

        self.player_id = player_id
        self.guild_id = guild_id
        self.category = category
        self.language = language

        if category == CATEGORY_ANIME:
            label = "شخصيات الأنمي" if language == "ar" else "Anime Characters"
            emoji = "⛩️"
        else:
            label = "شخصيات نتفلكس" if language == "ar" else "Netflix Characters"
            emoji = "🎬"

        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.primary
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "هذه القائمة ليست لك.",
                ephemeral=True
            )
            return

        view = CharacterSelectView(
            self.player_id,
            self.guild_id,
            self.category,
            self.language
        )

        title = (
            "اختر شخصيتك"
            if self.language == "ar"
            else "Choose Your Character"
        )

        await interaction.response.edit_message(
            embed=build_embed(
                f"🎭 {title}",
                (
                    "اختر شخصية من القائمة بالأسفل."
                    if self.language == "ar"
                    else "Select a character from the menu below."
                )
            ),
            view=view
        )


class CharacterHomeView(discord.ui.View):

    def __init__(self, player_id, guild_id, language):

        super().__init__(timeout=120)

        self.add_item(
            CharacterCategoryButton(
                player_id,
                guild_id,
                CATEGORY_ANIME,
                language
            )
        )

        self.add_item(
            CharacterCategoryButton(
                player_id,
                guild_id,
                CATEGORY_NETFLIX,
                language
            )
        )


# ========================================================
# LEADERBOARD
# ========================================================

def create_leaderboard_embed(guild, language, seasonal=False):

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
            description = f"**{season['name']}**\n\n{no_players}"

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

    return build_embed(title, description)


async def refresh_leaderboard(guild):

    embeds = [
        create_leaderboard_embed(guild, "ar", False),
        create_leaderboard_embed(guild, "ar", True),
        create_leaderboard_embed(guild, "en", False),
        create_leaderboard_embed(guild, "en", True),
    ]

    return await refresh_leaderboard_message(guild, embeds)


async def refresh_leaderboard_message(guild, embeds):

    channel = await fetch_text_channel(LEADERBOARD_CHANNEL_ID)

    if channel is None:
        return False

    saved = get_bot_message(guild.id, "leaderboard_panel")

    if saved:

        try:

            old_channel = await bot.fetch_channel(
                int(saved["channel_id"])
            )

            old_message = await old_channel.fetch_message(
                int(saved["message_id"])
            )

            if old_channel.id == channel.id:

                await old_message.edit(embeds=embeds)
                return True

            await old_message.delete()

        except discord.NotFound:
            pass

        except discord.Forbidden:
            logger.error("Cannot update leaderboard.")
            return False

        except discord.HTTPException:
            logger.exception("Leaderboard update failed.")
            return False

    try:

        message = await channel.send(embeds=embeds)

        save_bot_message(
            guild.id,
            "leaderboard_panel",
            channel.id,
            message.id
        )

        return True

    except discord.HTTPException:
        logger.exception("Could not create leaderboard.")
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

    channel = await fetch_text_channel(
        ACHIEVEMENTS_CHANNEL_ID
    )

    if channel is None:
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

    embed = build_embed(title, description)

    try:
        await channel.send(embed=embed)
        return True

    except discord.HTTPException:
        logger.exception("Achievement announcement failed.")
        return False


async def refresh_player_card_for_member(guild, member, language):
    """Update an existing public player card after a game result."""
    if language not in ("ar", "en"):
        return False

    saved = get_bot_message(guild.id, f"player_card:{member.id}")
    if not saved:
        return False

    embed = create_player_card_embed(guild, member, language)
    if embed is None:
        return False

    try:
        channel = await bot.fetch_channel(int(saved["channel_id"]))
        message = await channel.fetch_message(int(saved["message_id"]))
        await message.edit(embed=embed)
        return True
    except discord.NotFound:
        logger.warning("Player card message missing for user %s", member.id)
        return False
    except (discord.Forbidden, discord.HTTPException):
        logger.exception("Could not refresh player card for user %s", member.id)
        return False


@bot.event
async def on_arcade_game_finished(
    guild_id,
    user_id,
    language,
    result,
    game_id
):
    """Refresh public progression panels after a game is recorded."""
    guild = bot.get_guild(guild_id)
    if guild is None:
        return

    try:
        await refresh_leaderboard(guild)
    except Exception:
        logger.exception("Could not refresh leaderboard after game %s", game_id)

    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            logger.warning("Could not find player %s after game %s", user_id, game_id)
            return

    try:
        await refresh_player_card_for_member(guild, member, language)
    except Exception:
        logger.exception("Could not refresh player card after game %s", game_id)


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

    panel = build_embed(
        "🎮 بطاقات اللاعبين | Player Cards",
        (
            "اضغط الزر بالأسفل لإنشاء بطاقة لاعبك أو تحديثها.\n"
            "Your player card will be created or updated here.\n\n"
            "💜 بطاقة واحدة لكل لاعب، بدون تكرار."
        )
    )

    await ensure_saved_embed_message(
        guild,
        "player_card_panel",
        PLAYER_CARDS_CHANNEL_ID,
        panel,
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
    logger.info("💜 MHN ARCADE V2.0")
    logger.info("Logged in as: %s", bot.user)
    logger.info("Bot ID: %s", bot.user.id)
    logger.info("Servers: %s", len(bot.guilds))
    logger.info("Status: ONLINE")
    logger.info("=" * 45)

    await initialize_welcome_messages()

    for guild in bot.guilds:

        try:
            await initialize_arcade_systems(guild)

        except Exception:
            logger.exception(
                "Failed to initialize systems for %s",
                guild.name
            )


# ========================================================
# PLAYER REGISTRATION
# ========================================================

@bot.event
async def on_member_join(member: discord.Member):

    if member.bot:
        return

    create_player(
        member.guild.id,
        member.id,
        member.name
    )

    logger.info(
        "New player registered: %s (%s)",
        member.name,
        member.id
    )


# ========================================================
# UPDATE ANNOUNCEMENT COMMAND
# ========================================================

@bot.tree.command(
    name="announce_update",
    description="Publish an MHN ARCADE update announcement"
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    version="Update version, for example V2.1",
    additions="New features added in this update",
    improvements="Existing features that were improved",
    fixes="Bugs and issues fixed in this update"
)
async def announce_update_command(
    interaction: discord.Interaction,
    version: str,
    additions: str = "",
    improvements: str = "",
    fixes: str = ""
):
    await interaction.response.defer(ephemeral=True)

    if not version.strip() or len(version) > 30:
        await interaction.followup.send(
            "اكتب رقم إصدار صحيحًا (بحد أقصى 30 حرفًا).",
            ephemeral=True
        )
        return

    if any(len(value) > 1000 for value in (additions, improvements, fixes)):
        await interaction.followup.send(
            "كل قسم من تفاصيل التحديث يجب ألا يتجاوز 1000 حرف.",
            ephemeral=True
        )
        return

    channel = await fetch_text_channel(ARCADE_NEWS_CHANNEL_ID)
    if channel is None or channel.guild.id != interaction.guild.id:
        await interaction.followup.send(
            "تعذر العثور على قناة أخبار MHN ARCADE أو أنها ليست في هذا السيرفر.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"🚀 MHN ARCADE {version} — UPDATE",
        description="💜 صدر تحديث جديد! إليكم أبرز التغييرات والإضافات.",
        color=PURPLE
    )

    sections = (
        ("✨ الإضافات الجديدة | New Additions", additions),
        ("⚙️ التحسينات | Improvements", improvements),
        ("🛠️ الإصلاحات | Bug Fixes", fixes),
    )

    for title, content in sections:
        if content.strip():
            embed.add_field(name=title, value=content.strip(), inline=False)

    if not embed.fields:
        embed.description = (
            "💜 صدر تحديث جديد لـ MHN ARCADE.\n"
            "A new MHN ARCADE update is now available."
        )

    embed.set_footer(text=f"MHN ARCADE {version} • PLAY • COMPETE • WIN")

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send(
            "البوت لا يملك صلاحية إرسال الرسائل في قناة الأخبار.",
            ephemeral=True
        )
        return
    except discord.HTTPException:
        logger.exception("Could not publish update announcement.")
        await interaction.followup.send(
            "تعذر نشر إعلان التحديث بسبب خطأ من Discord.",
            ephemeral=True
        )
        return

    await interaction.followup.send(
        f"✅ تم نشر إعلان MHN ARCADE {version} في قناة الأخبار.",
        ephemeral=True
    )


# ========================================================
# PING COMMAND
# ========================================================

@bot.tree.command(
    name="ping",
    description="Check MHN ARCADE V2.0 connection"
)
async def ping(interaction: discord.Interaction):

    latency = round(bot.latency * 1000)

    embed = build_embed(
        "💜 MHN ARCADE V2.0",
        (
            "The arcade system is online!\n\n"
            f"🏓 **Ping:** {latency} ms"
        )
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ========================================================
# WALLET COMMAND
# ========================================================

@bot.tree.command(
    name="wallet",
    description="View your wallet and bank balance"
)
@app_commands.guild_only()
async def wallet_command(interaction: discord.Interaction):

    wallet = get_wallet(
        interaction.guild.id,
        interaction.user.id
    )

    language = get_language(
        interaction.guild.id,
        interaction.user.id
    )

    if language == "ar":

        embed = build_embed(
            "🪙 محفظتك",
            (
                f"👤 اللاعب: {interaction.user.mention}\n\n"
                f"💰 **المحفظة:** {wallet['coins']:,} عملة\n"
                f"🏦 **البنك:** {wallet['bank']:,} عملة\n"
                f"💎 **الإجمالي:** "
                f"{wallet['coins'] + wallet['bank']:,} عملة"
            )
        )

    else:

        embed = build_embed(
            "🪙 Your Wallet",
            (
                f"👤 Player: {interaction.user.mention}\n\n"
                f"💰 **Wallet:** {wallet['coins']:,} coins\n"
                f"🏦 **Bank:** {wallet['bank']:,} coins\n"
                f"💎 **Total:** "
                f"{wallet['coins'] + wallet['bank']:,} coins"
            )
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ========================================================
# DEPOSIT COMMAND
# ========================================================

@bot.tree.command(
    name="deposit",
    description="Deposit coins into your bank"
)
@app_commands.guild_only()
@app_commands.describe(
    amount="Number of coins to deposit"
)
async def deposit_command(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 1000000]
):

    success = deposit_coins(
        interaction.guild.id,
        interaction.user.id,
        amount
    )

    language = get_language(
        interaction.guild.id,
        interaction.user.id
    )

    if success:

        message = (
            f"✅ تم إيداع **{amount:,}** عملة في البنك."
            if language == "ar"
            else f"✅ Deposited **{amount:,}** coins into your bank."
        )

    else:

        message = (
            "❌ رصيد محفظتك غير كافٍ."
            if language == "ar"
            else "❌ You don't have enough coins in your wallet."
        )

    await interaction.response.send_message(
        message,
        ephemeral=True
    )


# ========================================================
# WITHDRAW COMMAND
# ========================================================

@bot.tree.command(
    name="withdraw",
    description="Withdraw coins from your bank"
)
@app_commands.guild_only()
@app_commands.describe(
    amount="Number of coins to withdraw"
)
async def withdraw_command(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 1000000]
):

    success = withdraw_coins(
        interaction.guild.id,
        interaction.user.id,
        amount
    )

    language = get_language(
        interaction.guild.id,
        interaction.user.id
    )

    if success:

        message = (
            f"✅ تم سحب **{amount:,}** عملة من البنك."
            if language == "ar"
            else f"✅ Withdrew **{amount:,}** coins from your bank."
        )

    else:

        message = (
            "❌ رصيد البنك غير كافٍ."
            if language == "ar"
            else "❌ You don't have enough coins in your bank."
        )

    await interaction.response.send_message(
        message,
        ephemeral=True
    )


# ========================================================
# CHARACTER COMMAND
# ========================================================

@bot.tree.command(
    name="character",
    description="Choose your anime or Netflix character"
)
@app_commands.guild_only()
async def character_command(interaction: discord.Interaction):

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

    view = CharacterHomeView(
        interaction.user.id,
        interaction.guild.id,
        language
    )

    if language == "ar":

        embed = build_embed(
            "🎭 اختر شخصيتك",
            (
                "مرحبًا بك في نظام الشخصيات!\n\n"
                "⛩️ **شخصيات الأنمي** — 15 شخصية\n"
                "🎬 **شخصيات نتفلكس** — 12 شخصية\n\n"
                "اختر القسم الذي تريده."
            )
        )

    else:

        embed = build_embed(
            "🎭 Choose Your Character",
            (
                "Welcome to the character system!\n\n"
                "⛩️ **Anime Characters** — 15 characters\n"
                "🎬 **Netflix Characters** — 12 characters\n\n"
                "Choose your category."
            )
        )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )


# ========================================================
# LANGUAGE SWITCH CONFIRMATION
# ========================================================

class LanguageConfirmationView(discord.ui.View):

    def __init__(
        self,
        member_id,
        guild_id,
        username,
        language
    ):

        super().__init__(timeout=120)

        self.member_id = member_id
        self.guild_id = guild_id
        self.username = username
        self.language = language

    async def interaction_check(self, interaction):

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

        select_language(
            guild_id=self.guild_id,
            user_id=self.member_id,
            username=self.username,
            language=self.language
        )

        for item in self.children:
            item.disabled = True

        if self.language == "ar":

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

        await interaction.response.edit_message(
            embed=build_embed(title, description),
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
            content="💜 Language change cancelled. Your progress remains unchanged.",
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
async def language_command(
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

        message = (
            "💜 أنت تستخدم هذه اللغة بالفعل."
            if selected_language == "ar"
            else "💜 You are already using this language."
        )

        await interaction.response.send_message(
            message,
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

        message = (
            "💜 تم اختيار اللغة العربية بنجاح! رحلتك تبدأ الآن."
            if selected_language == "ar"
            else "💜 English selected successfully! Your journey starts now."
        )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )
        return

    if selected_language == "ar":

        title = "⚠️ تأكيد تغيير اللغة"

        description = (
            "هل أنت متأكد من تغيير اللغة إلى العربية؟\n\n"
            "🔴 **تنبيه:** تغيير اللغة سيؤدي إلى تصفير تقدمك "
            "في مساري العربية والإنجليزية، بما في ذلك المستوى "
            "وXP والإحصائيات والإنجازات.\n\n"
            "سيتم أيضًا تصفير إحصائيات المواسم النشطة فقط.\n"
            "أما المواسم المنتهية وألقابك الخاصة فستبقى محفوظة.\n\n"
            "لن يتم التغيير إلا بعد تأكيدك."
        )

    else:

        title = "⚠️ Confirm Language Change"

        description = (
            "Are you sure you want to switch to English?\n\n"
            "🔴 **Warning:** Switching languages will reset your "
            "progress in both language tracks, including levels, "
            "XP, statistics, and achievements.\n\n"
            "Active season statistics will also reset.\n"
            "Ended seasons and special titles remain preserved.\n\n"
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
# GLOBAL COMMAND ERROR HANDLER
# ========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    logger.exception(
        "Application command error",
        exc_info=error
    )

    language = (
        get_language(interaction.guild.id, interaction.user.id)
        if interaction.guild is not None
        else None
    )

    if isinstance(error, app_commands.MissingPermissions):
        message = (
            "❌ تحتاج صلاحية **Manage Server** لاستخدام هذا الأمر."
            if language == "ar"
            else "❌ You need the **Manage Server** permission to use this command."
        )
    else:
        message = (
            "حدث خطأ أثناء تنفيذ الأمر. حاول مرة أخرى."
            if language == "ar"
            else "An error occurred while executing this command. Please try again."
        )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except discord.HTTPException:
        pass


# ========================================================
# START BOT
# ========================================================

if __name__ == "__main__":

    logger.info("Starting MHN ARCADE V2.0...")

    bot.run(TOKEN)
