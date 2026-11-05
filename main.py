
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
)


# ========================================================
# CONFIGURATION
# ========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing!")

# Arcade channels
ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910

# Theme
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

# Required for detecting new members
intents.members = True

# Message Content Intent is not required for our slash commands.


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

        self.welcome_messages_checked = False

    async def setup_hook(self):

        # Initialize database
        initialize_database()

        # Synchronize slash commands
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
# PERSISTENT WELCOME MESSAGE
# ========================================================

async def ensure_welcome_message(
    guild: discord.Guild,
    message_key: str,
    channel_id: int,
    embed: discord.Embed
):

    # Check whether this welcome message was sent before
    saved_message = get_bot_message(
        guild.id,
        message_key
    )

    if saved_message:

        try:
            await bot.fetch_channel(
                int(saved_message["channel_id"])
            )

            await bot.get_channel(
                int(saved_message["channel_id"])
            ).fetch_message(
                int(saved_message["message_id"])
            )

            logger.info(
                "Welcome message already exists: %s",
                message_key
            )

            return

        except (discord.NotFound, discord.HTTPException, AttributeError):
            logger.warning(
                "Saved welcome message could not be found. "
                "A replacement will be created."
            )

        except discord.Forbidden:
            logger.error(
                "Missing permissions to read the saved welcome message."
            )
            return

    # Get target channel
    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            logger.error(
                "Could not access welcome channel %s",
                channel_id
            )
            return

    if not isinstance(channel, discord.TextChannel):
        logger.error(
            "Welcome destination is not a text channel: %s",
            channel_id
        )
        return

    if channel.guild.id != guild.id:
        return

    try:

        message = await channel.send(
            embed=embed
        )

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

    except discord.Forbidden:
        logger.error(
            "Missing permission to send welcome message in %s",
            channel.name
        )

    except discord.HTTPException as error:
        logger.error(
            "Failed to send welcome message: %s",
            error
        )


async def initialize_welcome_messages():

    for guild in bot.guilds:

        await ensure_welcome_message(
            guild=guild,
            message_key="welcome_ar",
            channel_id=ARABIC_ARCADE_CHANNEL_ID,
            embed=create_arabic_welcome()
        )

        await ensure_welcome_message(
            guild=guild,
            message_key="welcome_en",
            channel_id=ENGLISH_ARCADE_CHANNEL_ID,
            embed=create_english_welcome()
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

    # Prevent duplicate welcome messages after reconnecting
    if not bot.welcome_messages_checked:

        await initialize_welcome_messages()

        bot.welcome_messages_checked = True


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

        language_name = (
            "العربية" if language == "ar"
            else "English"
        )

        embed = discord.Embed(
            title="💜 Language Updated",
            description=(
                f"Your language is now **{language_name}**.\n\n"
                "Your new player progress starts at Level 0 "
                "with 0 XP."
            ),
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

    # First-time player registration
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

    # Same language selected
    if current_language == selected_language:

        await interaction.response.send_message(
            "💜 You are already using this language.",
            ephemeral=True
        )

        return

    # First language selection: no reset required
    if current_language is None:

        select_language(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            username=interaction.user.name,
            language=selected_language
        )

        language_name = (
            "العربية" if selected_language == "ar"
            else "English"
        )

        embed = discord.Embed(
            title="💜 Language Selected",
            description=(
                f"Your arcade language is now **{language_name}**!\n\n"
                "🎮 Your journey starts at Level 0."
            ),
            color=PURPLE
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        return

    # Switching language requires explicit confirmation
    if selected_language == "ar":

        title = "⚠️ تأكيد تغيير اللغة"

        description = (
            "هل أنت متأكد من تغيير اللغة إلى العربية؟\n\n"
            "🔴 **تنبيه:** تغيير اللغة سيؤدي إلى تصفير "
            "تقدمك في مساري العربية والإنجليزية، "
            "بما في ذلك المستوى وXP والإحصائيات والإنجازات.\n\n"
            "لن يتم التغيير إلا بعد تأكيدك."
        )

    else:

        title = "⚠️ Confirm Language Change"

        description = (
            "Are you sure you want to switch to English?\n\n"
            "🔴 **Warning:** Switching languages will reset "
            "your progress in both Arabic and English tracks, "
            "including levels, XP, statistics, and achievements.\n\n"
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
# GLOBAL ERROR HANDLER
# ========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

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
