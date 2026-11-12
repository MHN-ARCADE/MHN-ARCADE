
"""MHN ARCADE V3 - Public XP card and profile language controls."""

from __future__ import annotations

import asyncio
import logging

import discord

from characters import get_character
from player_cards_v3 import (
    PLAYER_CARDS_CHANNEL_ID,
    PlayerCardPanelView,
    rank_for_level,
)
from player_profiles_v3 import (
    get_player_profile,
    save_player_profile,
)

logger = logging.getLogger("MHN_ARCADE.V3.PROGRESS_PANEL")

CARD_DURATION = 150

ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910

RANK_STYLE = {
    "ROOKIE": (0x64748B, "مبتدئ"),
    "APPRENTICE": (0x22C55E, "متدرب"),
    "PRO": (0x3B82F6, "محترف"),
    "ELITE": (0x06B6D4, "إيليت"),
    "MASTER": (0xF59E0B, "ماستر"),
    "MANAGER": (0xEF4444, "مانجر"),
    "GRANDMASTER": (0xA855F7, "جراند ماستر"),
    "MYTHIC": (0xF97316, "ميثيك"),
}


def build_xp_level_embed(
    member: discord.abc.User,
    profile,
    progress: dict,
) -> discord.Embed:
    """Build a bilingual-by-profile-language XP card."""

    language = str(profile["profile_language"])
    level = int(progress["level"])
    current_xp = int(progress["xp"])
    required_xp = max(1, int(progress["xp_to_next_level"]))
    total_xp = int(progress["total_xp"])

    rank = rank_for_level(level)
    color, arabic_rank = RANK_STYLE.get(
        rank,
        RANK_STYLE["ROOKIE"],
    )

    percentage = min(
        100,
        int(current_xp * 100 / required_xp),
    )

    filled = min(12, int(percentage * 12 / 100))
    progress_bar = "▰" * filled + "▱" * (12 - filled)

    character = get_character(profile["character_id"])

    character_image = (
        character.get("image_url")
        if character
        else None
    )

    if language == "ar":
        character_name = (
            character.get("name_ar") or character.get("name")
            if character else "غير محددة"
        )

        embed = discord.Embed(
            title="⚡ بطاقة المستوى والخبرة",
            description=(
                f"{member.mention}\n"
                f"**{discord.utils.escape_markdown(member.display_name)}**\n"
                f"الرتبة الحالية: **{arabic_rank}**"
            ),
            color=color,
        )

        embed.add_field(
            name="⭐ المستوى",
            value=f"**LEVEL {level}**",
            inline=True,
        )
        embed.add_field(
            name="🏆 الرتبة",
            value=f"**{arabic_rank}**",
            inline=True,
        )
        embed.add_field(
            name="📚 إجمالي XP",
            value=f"**{total_xp:,}**",
            inline=True,
        )
        embed.add_field(
            name="📈 التقدم للمستوى القادم",
            value=(
                f"`{progress_bar}` **{percentage}%**\n"
                f"**{current_xp:,} / {required_xp:,} XP**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎭 الشخصية المختارة",
            value=f"**{character_name}**",
            inline=False,
        )
        embed.set_footer(
            text="MHN ARCADE • رحلة التقدم مستمرة"
        )

    else:
        character_name = (
            character.get("name") or character.get("name_ar")
            if character else "Not selected"
        )

        embed = discord.Embed(
            title="⚡ XP / LEVEL CARD",
            description=(
                f"{member.mention}\n"
                f"**{discord.utils.escape_markdown(member.display_name)}**\n"
                f"Current Rank: **{rank}**"
            ),
            color=color,
        )

        embed.add_field(
            name="⭐ Level",
            value=f"**LEVEL {level}**",
            inline=True,
        )
        embed.add_field(
            name="🏆 Rank",
            value=f"**{rank}**",
            inline=True,
        )
        embed.add_field(
            name="📚 Total XP",
            value=f"**{total_xp:,}**",
            inline=True,
        )
        embed.add_field(
            name="📈 Next Level Progress",
            value=(
                f"`{progress_bar}` **{percentage}%**\n"
                f"**{current_xp:,} / {required_xp:,} XP**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎭 Selected Character",
            value=f"**{character_name}**",
            inline=False,
        )
        embed.set_footer(
            text="MHN ARCADE • YOUR JOURNEY CONTINUES"
        )

    # Keep the selected character image original and untouched.
    if character_image:
        embed.set_thumbnail(url=character_image)

    return embed


async def publish_xp_card(
    guild: discord.Guild,
    member: discord.abc.User,
    profile,
    progress: dict,
) -> bool:
    """Publish the XP card publicly for 150 seconds."""

    embed = build_xp_level_embed(
        member,
        profile,
        progress,
    )

    try:
        channel = guild.get_channel(PLAYER_CARDS_CHANNEL_ID)

        if channel is None:
            channel = await guild.fetch_channel(
                PLAYER_CARDS_CHANNEL_ID
            )

        if not isinstance(channel, discord.TextChannel):
            logger.error("Player cards channel is not a text channel.")
            return False

        message = await channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    except (discord.Forbidden, discord.HTTPException):
        logger.exception(
            "Failed to publish XP card for user %s",
            member.id,
        )
        return False

    async def delete_later():
        await asyncio.sleep(CARD_DURATION)

        try:
            await message.delete()
        except discord.NotFound:
            pass
        except (discord.Forbidden, discord.HTTPException):
            logger.exception(
                "Failed to delete XP card for user %s",
                member.id,
            )

    asyncio.create_task(delete_later())
    return True


async def send_missing_profile_notice(
    interaction: discord.Interaction,
    language: str,
):
    channel = f"<#{PLAYER_CARDS_CHANNEL_ID}>"

    if language == "ar":
        dm = (
            "💜 ما أنشأت بطاقة لاعبك حتى الآن!\n"
            f"توجه إلى {channel} واضغط زر بطاقة اللاعب "
            "وأنشئ بطاقتك أولًا."
        )
        private_notice = "أرسلت لك رسالة خاصة فيها طريقة إنشاء بطاقتك."
    else:
        dm = (
            "💜 You haven't created your player card yet!\n"
            f"Go to {channel}, press Player Card, and create your profile first."
        )
        private_notice = "I sent you a DM with instructions to create your player card."

    try:
        await interaction.user.send(dm)
        await interaction.followup.send(
            private_notice,
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            dm,
            ephemeral=True,
        )


class LanguageChoiceButton(discord.ui.Button):

    def __init__(self, owner_id: int, language: str):
        self.owner_id = owner_id
        self.language = language

        super().__init__(
            label="العربية" if language == "ar" else "English",
            emoji="🇸🇦" if language == "ar" else "🇬🇧",
            style=discord.ButtonStyle.primary,
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "هذه القائمة ليست لك." if self.language == "ar"
                else "This menu is not yours.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "استخدم هذا الخيار داخل السيرفر."
                if self.language == "ar"
                else "Use this option inside the server.",
                ephemeral=True,
            )
            return

        profile = get_player_profile(
            interaction.guild.id,
            interaction.user.id,
        )

        if profile is None:
            await interaction.response.send_message(
                "أنشئ بطاقة لاعبك أولًا."
                if self.language == "ar"
                else "Create your player card first.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Change language only. Preserve character and progression.
        save_player_profile(
            interaction.guild.id,
            interaction.user.id,
            self.language,
            profile["character_id"],
        )

        channel_id = (
            ARABIC_ARCADE_CHANNEL_ID
            if self.language == "ar"
            else ENGLISH_ARCADE_CHANNEL_ID
        )
        arcade_channel = f"<#{channel_id}>"

        if self.language == "ar":
            dm = (
                "💜 تم تغيير لغة ملفك إلى العربية بنجاح!\n"
                "مستواك وXP وشخصيتك وإنجازاتك محفوظة كما هي.\n\n"
                f"🎮 قناة الألعاب: {arcade_channel}\n"
                "ادخل وواصل اللعب!"
            )
            confirmation = "💜 تغيرت لغتك إلى العربية. أرسلت لك رسالة خاصة."
        else:
            dm = (
                "💜 Your profile language is now English!\n"
                "Your level, XP, character, and achievements are unchanged.\n\n"
                f"🎮 Your arcade channel: {arcade_channel}\n"
                "Head there and keep playing!"
            )
            confirmation = "💜 Your language is now English. I sent you a DM."

        try:
            await interaction.user.send(dm)
            await interaction.followup.send(
                confirmation,
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"{confirmation}\n\n{dm}",
                ephemeral=True,
            )


class LanguageChoiceView(discord.ui.View):

    def __init__(self, owner_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id

        self.add_item(LanguageChoiceButton(owner_id, "ar"))
        self.add_item(LanguageChoiceButton(owner_id, "en"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "هذه القائمة ليست لك."
                if interaction.locale.value.startswith("ar")
                else "This menu is not yours.",
                ephemeral=True,
            )
            return False
        return True


class XPLevelButton(discord.ui.Button):

    def __init__(self, runtime):
        self.runtime = runtime

        super().__init__(
            label="XP / Level",
            emoji="⚡",
            style=discord.ButtonStyle.success,
            custom_id="mhn_arcade:v3:xp_level",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.guild is None:
            await interaction.response.send_message(
                "استخدم هذا الزر داخل السيرفر."
                if interaction.locale.value.startswith("ar")
                else "Use this button inside the server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        profile = get_player_profile(
            interaction.guild.id,
            interaction.user.id,
        )

        if profile is None:
            await send_missing_profile_notice(
                interaction,
                "ar" if interaction.locale.value.startswith("ar") else "en",
            )
            return

        try:
            progress = await self.runtime.progression.get_player_progress(
                interaction.guild.id,
                interaction.user.id,
                interaction.user.display_name,
            )

            published = await publish_xp_card(
                interaction.guild,
                interaction.user,
                profile,
                progress,
            )

            if profile["profile_language"] == "ar":
                result = (
                    "⚡ تم نشر بطاقة المستوى للجميع لمدة دقيقتين و30 ثانية."
                    if published
                    else "تعذر نشر البطاقة الآن، حاول مرة ثانية."
                )
            else:
                result = (
                    "⚡ Your XP card is public for 2 minutes and 30 seconds."
                    if published
                    else "Could not publish your XP card. Please try again."
                )

            await interaction.followup.send(
                result,
                ephemeral=True,
            )

        except Exception:
            logger.exception(
                "XP card error for user %s",
                interaction.user.id,
            )
            await interaction.followup.send(
                "تعذر تحميل بيانات مستواك، حاول مرة ثانية."
                if profile["profile_language"] == "ar"
                else "Could not load your level data. Please try again.",
                ephemeral=True,
            )


class ChangeLanguageButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Language | اللغة",
            emoji="🌐",
            style=discord.ButtonStyle.secondary,
            custom_id="mhn_arcade:v3:change_language",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.guild is None:
            await interaction.response.send_message(
                "استخدم هذا الزر داخل السيرفر."
                if interaction.locale.value.startswith("ar")
                else "Use this button inside the server.",
                ephemeral=True,
            )
            return

        profile = get_player_profile(
            interaction.guild.id,
            interaction.user.id,
        )

        if profile is None:
            await interaction.response.send_message(
                "أنشئ بطاقة لاعبك أولًا حتى تقدر تغيّر اللغة."
                if interaction.locale.value.startswith("ar")
                else "Create your player card first to change your language.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "اختر اللغة التي تفضلها:"
            if profile["profile_language"] == "ar"
            else "Choose your preferred language:",
            view=LanguageChoiceView(interaction.user.id),
            ephemeral=True,
        )


class V3PlayerCardPanelView(PlayerCardPanelView):

    def __init__(self, runtime):
        super().__init__()

        self.add_item(XPLevelButton(runtime))
        self.add_item(ChangeLanguageButton())
