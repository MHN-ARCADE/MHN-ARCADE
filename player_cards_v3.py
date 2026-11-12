
"""MHN ARCADE V3 - bilingual player-card workflow."""

from __future__ import annotations

import asyncio
import logging

import discord

from characters import (
    CATEGORY_ANIME,
    CATEGORY_NETFLIX,
    get_character,
    get_characters_by_category,
)
from database import (
    create_player,
    ensure_progress,
    get_achievement_count,
    get_progress,
    get_selected_character,
    get_wallet,
    select_character,
    xp_required_for_next_level,
)
from player_profiles_v3 import get_player_profile, save_player_profile

logger = logging.getLogger("MHN_ARCADE.V3.PLAYER_CARDS")

PLAYER_CARDS_CHANNEL_ID = 1567719418862112809
ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910
PURPLE = 0x7C3AED

# Public player cards remain visible for 2 minutes and 30 seconds.
PUBLIC_CARD_SECONDS = 150


def rank_for_level(level: int) -> str:
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


def build_player_card_embed(
    guild: discord.Guild,
    member: discord.abc.User,
    profile,
    *,
    public: bool = False
) -> discord.Embed:

    language = profile["profile_language"]
    user_id = member.id

    progress = get_progress(guild.id, user_id, language)

    if progress is None:
        ensure_progress(guild.id, user_id, language)
        progress = get_progress(guild.id, user_id, language)

    if progress is None:
        raise RuntimeError("Could not load the player's progress track.")

    level = int(progress["level"])
    xp = int(progress["xp"])
    next_xp = xp_required_for_next_level(level)

    games = int(progress["games_played"])
    wins = int(progress["wins"])
    win_rate = (wins / games * 100) if games else 0.0

    achievements = get_achievement_count(
        guild.id,
        user_id,
        language
    )

    wallet = get_wallet(guild.id, user_id)

    selected = get_selected_character(guild.id, user_id)
    character = get_character(selected["character_id"]) if selected else None

    if character:
        character_name = (
            character["name_ar"]
            if language == "ar"
            else character["name"]
        )
    else:
        character_name = (
            "لم يتم اختيار شخصية"
            if language == "ar"
            else "No character selected"
        )

    filled = min(10, int((xp / max(1, next_xp)) * 10))
    bar = "🟪" * filled + "⬛" * (10 - filled)

    if language == "ar":

        embed = discord.Embed(
            title="💜 بطاقة اللاعب",
            description=(
                f"**{discord.utils.escape_markdown(member.display_name)}**\n"
                f"المعرّف: `{member.name}`\n"
                f"الرتبة: **{rank_for_level(level)}**\n"
                f"الشخصية: **{character_name}**"
            ),
            color=PURPLE,
        )

        fields = [
            ("⭐ المستوى", str(level), True),
            ("✨ XP", f"{xp:,} / {next_xp:,}", True),
            ("🏅 الإنجازات", str(achievements), True),
            ("📈 التقدم", bar, False),
            ("🎮 المباريات", str(games), True),
            ("🥇 الانتصارات", str(wins), True),
            ("📊 نسبة الفوز", f"{win_rate:.1f}%", True),
            ("🔥 أفضل سلسلة", str(progress["best_streak"]), True),
            ("🪙 المحفظة", f"{wallet['coins']:,}", True),
            ("🏦 البنك", f"{wallet['bank']:,}", True),
            ("📚 إجمالي XP", f"{int(progress['lifetime_xp']):,}", True),
        ]

    else:

        embed = discord.Embed(
            title="💜 Player Card",
            description=(
                f"**{discord.utils.escape_markdown(member.display_name)}**\n"
                f"Username: `{member.name}`\n"
                f"Rank: **{rank_for_level(level)}**\n"
                f"Character: **{character_name}**"
            ),
            color=PURPLE,
        )

        fields = [
            ("⭐ Level", str(level), True),
            ("✨ XP", f"{xp:,} / {next_xp:,}", True),
            ("🏅 Achievements", str(achievements), True),
            ("📈 Progress", bar, False),
            ("🎮 Games Played", str(games), True),
            ("🥇 Wins", str(wins), True),
            ("📊 Win Rate", f"{win_rate:.1f}%", True),
            ("🔥 Best Streak", str(progress["best_streak"]), True),
            ("🪙 Wallet", f"{wallet['coins']:,}", True),
            ("🏦 Bank", f"{wallet['bank']:,}", True),
            ("📚 Lifetime XP", f"{int(progress['lifetime_xp']):,}", True),
        ]

    for name, value, inline in fields:
        embed.add_field(name=name, value=value, inline=inline)

    if character and character.get("image_url"):
        embed.set_thumbnail(url=character["image_url"])

    embed.set_footer(text="MHN ARCADE V3 • PLAYER PROFILE")

    if public:
        embed.description = (
            (embed.description or "")
            + "\n\n💜 MHN ARCADE PLAYER"
        )

    return embed


async def _send_private_error(
    interaction: discord.Interaction,
    message: str
):
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


async def publish_temporary_player_card(
    guild: discord.Guild,
    member: discord.abc.User,
    profile
) -> bool:

    embed = build_player_card_embed(
        guild,
        member,
        profile,
        public=True
    )

    try:
        channel = guild.get_channel(PLAYER_CARDS_CHANNEL_ID)

        if channel is None:
            channel = await guild.fetch_channel(
                PLAYER_CARDS_CHANNEL_ID
            )

        public_message = await channel.send(embed=embed)

    except (discord.Forbidden, discord.HTTPException, AttributeError):
        logger.exception(
            "Could not publish temporary player card for %s",
            member.id
        )
        return False

    async def remove_public_card():

        await asyncio.sleep(PUBLIC_CARD_SECONDS)

        try:
            await public_message.delete()

        except discord.NotFound:
            pass

        except (discord.Forbidden, discord.HTTPException):
            logger.exception(
                "Could not remove temporary public card for %s",
                member.id
            )

    asyncio.create_task(remove_public_card())

    return True


class PlayerCardPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="بطاقة اللاعب | Player Card",
        emoji="🎮",
        style=discord.ButtonStyle.primary,
        custom_id="mhn_arcade:v3:player_card",
    )
    async def open_player_card(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await _send_private_error(
                interaction,
                "Use this button inside the server."
            )
            return

        profile = get_player_profile(
            interaction.guild.id,
            interaction.user.id
        )

        language = (
            profile["profile_language"]
            if profile
            else "en"
        )

        if profile:

            view = ExistingPlayerCardView(
                interaction.user.id,
                language
            )

            await interaction.response.send_message(
                content=(
                    "اختر الإجراء المطلوب:"
                    if language == "ar"
                    else "Choose an action:"
                ),
                view=view,
                ephemeral=True,
            )

        else:

            embed = discord.Embed(
                title="🎮 بطاقة اللاعب | Player Card",
                description=(
                    "ما عندك بطاقة لاعب للحين. أنشئ بطاقتك وابدأ رحلتك! 💜\n\n"
                    "You don't have a player card yet. Create yours and start your journey! 💜"
                ),
                color=PURPLE,
            )

            view = NewPlayerCardView(interaction.user.id)

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True
            )


class ExistingPlayerCardView(discord.ui.View):

    def __init__(self, owner_id: int, language: str):

        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.language = language

        view_button = discord.ui.Button(
            label=(
                "عرض بطاقة اللاعب"
                if language == "ar"
                else "View Player Card"
            ),
            emoji="👤",
            style=discord.ButtonStyle.success
        )

        change_button = discord.ui.Button(
            label=(
                "تغيير الشخصية"
                if language == "ar"
                else "Change Character"
            ),
            emoji="🎭",
            style=discord.ButtonStyle.primary
        )

        view_button.callback = self.show_card
        change_button.callback = self.change_character

        self.add_item(view_button)
        self.add_item(change_button)

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك."
                if self.language == "ar"
                else "This menu is not yours."
            )

            return False

        return True

    async def show_card(self, interaction: discord.Interaction):

        profile = get_player_profile(
            interaction.guild.id,
            interaction.user.id
        )

        if profile is None:

            await _send_private_error(
                interaction,
                "لم تعد بطاقتك موجودة."
                if self.language == "ar"
                else "Your profile no longer exists."
            )

            return

        published = await publish_temporary_player_card(
            interaction.guild,
            interaction.user,
            profile
        )

        if self.language == "ar":

            message = (
                "💜 تم نشر بطاقة لاعبك للعامة لمدة دقيقتين و30 ثانية."
                if published
                else "تعذر نشر البطاقة الآن، حاول مرة ثانية."
            )

        else:

            message = (
                "💜 Your player card is now public for 2 minutes and 30 seconds."
                if published
                else "Could not publish your card right now. Please try again."
            )

        await interaction.response.send_message(
            content=message,
            ephemeral=True
        )

    async def change_character(self, interaction: discord.Interaction):

        view = CharacterCategoryView(
            self.owner_id,
            self.language,
            mode="change"
        )

        title = (
            "اختر تصنيف الشخصية الجديدة"
            if self.language == "ar"
            else "Choose your new character category"
        )

        description = (
            "اختر من الأنمي أو نتفلكس."
            if self.language == "ar"
            else "Choose Anime or Netflix."
        )

        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(
                title=f"🎭 {title}",
                description=description,
                color=PURPLE
            ),
            view=view
        )


class NewPlayerCardView(discord.ui.View):

    def __init__(self, owner_id: int):

        super().__init__(timeout=180)

        self.owner_id = owner_id

        self.add_item(LanguageButton(owner_id, "ar"))
        self.add_item(LanguageButton(owner_id, "en"))

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك."
                if interaction.locale.value.startswith("ar")
                else "This menu is not yours."
            )

            return False

        return True


class LanguageButton(discord.ui.Button):

    def __init__(self, owner_id: int, language: str):

        self.owner_id = owner_id
        self.language = language

        super().__init__(
            label="العربية" if language == "ar" else "English",
            emoji="🇸🇦" if language == "ar" else "🇬🇧",
            style=discord.ButtonStyle.primary,
        )

    async def callback(self, interaction: discord.Interaction):

        view = CharacterCategoryView(
            self.owner_id,
            self.language
        )

        title = (
            "اختر تصنيف الشخصية"
            if self.language == "ar"
            else "Choose a character category"
        )

        description = (
            "اختر من الأنمي أو نتفلكس."
            if self.language == "ar"
            else "Choose Anime or Netflix."
        )

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"🎭 {title}",
                description=description,
                color=PURPLE
            ),
            view=view,
        )


class CharacterCategoryView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        language: str,
        mode: str = "create"
    ):

        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.language = language
        self.mode = mode

        self.add_item(
            CharacterCategoryButton(
                owner_id,
                language,
                CATEGORY_ANIME,
                mode
            )
        )

        self.add_item(
            CharacterCategoryButton(
                owner_id,
                language,
                CATEGORY_NETFLIX,
                mode
            )
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك."
                if self.language == "ar"
                else "This menu is not yours."
            )

            return False

        return True


class CharacterCategoryButton(discord.ui.Button):

    def __init__(
        self,
        owner_id: int,
        language: str,
        category: str,
        mode: str = "create"
    ):

        self.owner_id = owner_id
        self.language = language
        self.category = category
        self.mode = mode

        if category == CATEGORY_ANIME:

            label, emoji = (
                ("شخصيات الأنمي", "⛩️")
                if language == "ar"
                else ("Anime Characters", "⛩️")
            )

        else:

            label, emoji = (
                ("شخصيات نتفلكس", "🎬")
                if language == "ar"
                else ("Netflix Characters", "🎬")
            )

        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.primary
        )

    async def callback(self, interaction: discord.Interaction):

        characters = get_characters_by_category(self.category)
        options = []

        for item in characters[:25]:

            label = (
                item["name_ar"]
                if self.language == "ar"
                else item["name"]
            )

            series = item["series"]

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=item["id"],
                    description=series[:100]
                )
            )

        view = CharacterChoiceView(
            self.owner_id,
            self.language,
            options,
            self.mode
        )

        title = (
            "اختر شخصيتك"
            if self.language == "ar"
            else "Choose your character"
        )

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"🎭 {title}",
                description=(
                    "اختر شخصية من القائمة."
                    if self.language == "ar"
                    else "Select a character from the list."
                ),
                color=PURPLE
            ),
            view=view,
        )


class CharacterChoiceView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        language: str,
        options,
        mode: str = "create"
    ):

        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.language = language
        self.mode = mode

        self.add_item(
            CharacterChoiceSelect(
                owner_id,
                language,
                options,
                mode
            )
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك."
                if self.language == "ar"
                else "This menu is not yours."
            )

            return False

        return True


class CharacterChoiceSelect(discord.ui.Select):

    def __init__(
        self,
        owner_id: int,
        language: str,
        options,
        mode: str = "create"
    ):

        self.owner_id = owner_id
        self.language = language
        self.mode = mode

        super().__init__(
            placeholder=(
                "اختر شخصية"
                if language == "ar"
                else "Choose your character"
            ),
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        character_id = self.values[0]
        character = get_character(character_id)

        if character is None:

            await _send_private_error(
                interaction,
                "الشخصية غير موجودة."
                if self.language == "ar"
                else "Character not found."
            )

            return

        guild = interaction.guild

        if guild is None:

            await _send_private_error(
                interaction,
                "استخدمها داخل السيرفر."
                if self.language == "ar"
                else "Use this inside the server."
            )

            return

        try:

            if self.mode == "change":

                profile = get_player_profile(
                    guild.id,
                    interaction.user.id
                )

                if profile is None:

                    await _send_private_error(
                        interaction,
                        "بطاقتك غير موجودة، أنشئ بطاقة جديدة أولاً."
                        if self.language == "ar"
                        else "Your profile was not found. Please create a card first."
                    )

                    return

                # Preserve the existing profile language and V2 progress.
                save_player_profile(
                    guild.id,
                    interaction.user.id,
                    profile["profile_language"],
                    character_id
                )

            else:

                create_player(
                    guild.id,
                    interaction.user.id,
                    interaction.user.name
                )

                ensure_progress(
                    guild.id,
                    interaction.user.id,
                    self.language
                )

                save_player_profile(
                    guild.id,
                    interaction.user.id,
                    self.language,
                    character_id
                )

            # Save the selected character for the player card.
            select_character(
                guild.id,
                interaction.user.id,
                character_id
            )

            profile = get_player_profile(
                guild.id,
                interaction.user.id
            )

            published = await publish_temporary_player_card(
                guild,
                interaction.user,
                profile
            )

            if self.mode == "create":

                arcade_channel_id = (
                    ARABIC_ARCADE_CHANNEL_ID
                    if self.language == "ar"
                    else ENGLISH_ARCADE_CHANNEL_ID
                )

                arcade_mention = f"<#{arcade_channel_id}>"

                if self.language == "ar":

                    dm_text = (
                        f"💜 مبروك {interaction.user.mention}! "
                        "تم إنشاء بطاقة لاعبك بنجاح.\n\n"
                        f"قناة ألعابك: {arcade_mention}\n"
                        "منها تقدر تدخل الألعاب وتجمع XP "
                        "وترفع مستواك وتفتح الإنجازات والكؤوس."
                    )

                else:

                    dm_text = (
                        f"💜 Congratulations {interaction.user.mention}! "
                        "Your player card has been created successfully.\n\n"
                        f"Your arcade channel: {arcade_mention}\n"
                        "Play games there to earn XP, level up, "
                        "and unlock achievements and trophies."
                    )

                dm_sent = False

                try:

                    await interaction.user.send(dm_text)
                    dm_sent = True

                except (discord.Forbidden, discord.HTTPException):

                    logger.info(
                        "Could not DM player-card confirmation to %s",
                        interaction.user.id
                    )

                if published and dm_sent:

                    result_message = (
                        "💜 تم إنشاء بطاقة لاعبك بنجاح! "
                        "شيّك على الخاص، رسلت لك رسالة فيها التفاصيل."
                        if self.language == "ar"
                        else "💜 Your player card has been created! "
                        "Check your DMs — I sent you a message with the details."
                    )

                elif published:

                    result_message = (
                        "💜 تم إنشاء بطاقة لاعبك ونشرها للعامة! "
                        "لكن ما قدرت أرسل لك رسالة خاصة، تأكد من إعدادات الخاص."
                        if self.language == "ar"
                        else "💜 Your player card was created and published! "
                        "However, I couldn't DM you. Please check your privacy settings."
                    )

                else:

                    result_message = (
                        "تم إنشاء بطاقة لاعبك، لكن تعذر نشرها للعامة الآن."
                        if self.language == "ar"
                        else "Your player card was created, but could not be published publicly."
                    )

            else:

                if published:

                    result_message = (
                        "💜 تم تغيير شخصيتك ونشر بطاقة لاعبك للعامة لمدة دقيقتين و30 ثانية."
                        if self.language == "ar"
                        else "💜 Your character was changed and your player card is public for 2 minutes and 30 seconds."
                    )

                else:

                    result_message = (
                        "تم تغيير شخصيتك، لكن تعذر نشر البطاقة الآن."
                        if self.language == "ar"
                        else "Your character was changed, but the card could not be published right now."
                    )

            await interaction.response.edit_message(
                content=result_message,
                embed=None,
                view=None
            )

        except Exception:

            logger.exception(
                "V3 player-card workflow failed for %s",
                interaction.user.id
            )

            error_message = (
                "تعذر إكمال العملية، حاول مرة ثانية."
                if self.language == "ar"
                else "Could not complete the action. Please try again."
            )

            if interaction.response.is_done():

                await interaction.followup.send(
                    error_message,
                    ephemeral=True
                )

            else:

                await _send_private_error(
                    interaction,
                    error_message
                )
