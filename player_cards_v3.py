
"""MHN ARCADE V3 - bilingual player-card workflow with PNG output."""

from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path
import aiohttp
import discord

from characters import (
    CATEGORY_ANIME,
    CATEGORY_NETFLIX,
    get_character,
    get_characters_by_category,
)
from player_card_renderer import render_player_card_png
from player_profiles_v3 import get_player_profile, save_player_profile

logger = logging.getLogger("MHN_ARCADE.V3.PLAYER_CARDS")

PLAYER_CARDS_CHANNEL_ID = 1567719418862112809
ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910

PURPLE = 0x7C3AED
PUBLIC_CARD_SECONDS = 150


async def _send_private_error(
    interaction: discord.Interaction,
    message: str,
) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def _runtime_from_view(view: discord.ui.View):
    """Find the V3 runtime attached to the XP button in the parent panel."""

    runtime = getattr(view, "runtime", None)

    if runtime is not None:
        return runtime

    for item in getattr(view, "children", ()):
        runtime = getattr(item, "runtime", None)

        if runtime is not None:
            return runtime

    return None


async def _read_avatar(member: discord.abc.User) -> bytes | None:
    try:
        return await member.display_avatar.read()

    except (discord.HTTPException, OSError):
        logger.warning(
            "Could not read avatar for %s.",
            member.id,
            exc_info=True,
        )
        return None

async def _read_character_image(character) -> bytes | None:
    """Read the selected character artwork from the local repository."""

    if not character:
        return None

    image_file = character.get("image_file")

    if not image_file:
        logger.warning("Character has no local image filename.")
        return None

    image_path = Path(__file__).resolve().parent / image_file

    try:
        if not image_path.is_file():
            logger.warning(
                "Character image file was not found: %s",
                image_path.name,
            )
            return None

        if image_path.stat().st_size > 8 * 1024 * 1024:
            logger.warning(
                "Character image exceeds the 8 MB limit: %s",
                image_path.name,
            )
            return None

        return image_path.read_bytes()

    except OSError:
        logger.warning(
            "Could not read local character artwork: %s",
            image_file,
            exc_info=True,
        )
        return None

async def build_player_card_data(
    guild: discord.Guild,
    member: discord.abc.User,
    profile,
    runtime,
) -> tuple[dict, bytes | None, bytes | None]:

    """
    Build the player card using V3 profile and progression data.

    This function does not read wallet, bank, coins,
    or legacy V2 XP values.
    """

    if runtime is None:
        raise RuntimeError("V3 runtime is not available.")

    progression = getattr(runtime, "progression", None)

    if progression is None:
        raise RuntimeError("V3 progression manager is not available.")

    language = (
        "ar"
        if str(profile["profile_language"]).lower() == "ar"
        else "en"
    )

    progress = await progression.get_player_progress(
        guild.id,
        member.id,
        member.display_name,
    )

    character = get_character(profile["character_id"])

    if character:

        if language == "ar":
            character_name = (
                character.get("name_ar")
                or character.get("name")
                or "غير محددة"
            )
        else:
            character_name = (
                character.get("name")
                or character.get("name_ar")
                or "Not selected"
            )

    else:
        character_name = (
            "غير محددة"
            if language == "ar"
            else "Not selected"
        )

    games = max(
        0,
        int(progress.get("games_played", 0)),
    )

    wins = max(
        0,
        int(progress.get("wins", 0)),
    )

    draws = max(
        0,
        int(progress.get("draws", 0)),
    )

    losses = max(
        0,
        int(
            progress.get(
                "losses",
                max(0, games - wins - draws),
            )
        ),
    )

    win_rate = (
        wins / games * 100
        if games
        else 0.0
    )

    achievements_count = 0

    achievements_manager = getattr(
        runtime,
        "achievements",
        None,
    )

    if achievements_manager is not None:

        try:
            achievement_data = (
                await achievements_manager.get_player_stats(
                    member.id
                )
            )

            achievements_count = len(
                achievement_data.get("achievements", [])
            )

        except Exception:
            logger.warning(
                "Could not load V3 achievements for user %s.",
                member.id,
                exc_info=True,
            )

    data = {
        "language": language,
        "player_name": member.display_name,
        "username": member.name,

        "rank": str(
            progress.get("rank", "ROOKIE")
        ).upper(),

        "level": int(
            progress.get("level", 1)
        ),

        "total_xp": int(
            progress.get("total_xp", 0)
        ),

        "current_xp": int(
            progress.get("xp", 0)
        ),

        "required_xp": max(
            1,
            int(progress.get("xp_to_next_level", 1)),
        ),

        "character_name": character_name,

        "games": games,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,

        "achievements": achievements_count,
    }

    avatar_bytes, character_bytes = await asyncio.gather(
        _read_avatar(member),
        _read_character_image(character),
    )

    return data, avatar_bytes, character_bytes


async def publish_temporary_player_card(
    guild: discord.Guild,
    member: discord.abc.User,
    profile,
    runtime,
) -> bool:

    try:

        data, avatar_bytes, character_bytes = (
            await build_player_card_data(
                guild,
                member,
                profile,
                runtime,
            )
        )

        png_bytes = render_player_card_png(
            data,
            avatar_bytes=avatar_bytes,
            character_bytes=character_bytes,
        )

        channel = guild.get_channel(
            PLAYER_CARDS_CHANNEL_ID
        )

        if channel is None:
            channel = await guild.fetch_channel(
                PLAYER_CARDS_CHANNEL_ID
            )

        if not isinstance(channel, discord.TextChannel):
            logger.error(
                "Player cards channel is not a text channel."
            )
            return False

        image_file = discord.File(
            fp=io.BytesIO(png_bytes),
            filename=f"player-card-{member.id}.png",
        )

        public_message = await channel.send(
            file=image_file,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    except (
        discord.Forbidden,
        discord.HTTPException,
        aiohttp.ClientError,
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
    ):

        logger.exception(
            "Could not publish PNG player card for %s.",
            member.id,
        )
        return False

    except Exception:

        logger.exception(
            "Unexpected player-card error for %s.",
            member.id,
        )
        return False

    async def remove_public_card():

        await asyncio.sleep(PUBLIC_CARD_SECONDS)

        try:
            await public_message.delete()

        except discord.NotFound:
            pass

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            logger.exception(
                "Could not remove temporary public card for %s.",
                member.id,
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
        button: discord.ui.Button,
    ):

        if interaction.guild is None:
            await _send_private_error(
                interaction,
                "Use this button inside the server.",
            )
            return

        runtime = _runtime_from_view(self)

        profile = get_player_profile(
            interaction.guild.id,
            interaction.user.id,
        )

        language = (
            profile["profile_language"]
            if profile
            else "en"
        )

        if profile:

            view = ExistingPlayerCardView(
                interaction.user.id,
                language,
                runtime,
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
                    "ما عندك بطاقة لاعب للحين. "
                    "أنشئ بطاقتك وابدأ رحلتك! 💜\n\n"
                    "You don't have a player card yet. "
                    "Create yours and start your journey! 💜"
                ),
                color=PURPLE,
            )

            view = NewPlayerCardView(
                interaction.user.id,
                runtime,
            )

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True,
            )


class ExistingPlayerCardView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        language: str,
        runtime,
    ):

        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.language = language
        self.runtime = runtime

        view_button = discord.ui.Button(
            label=(
                "عرض بطاقة اللاعب"
                if language == "ar"
                else "View Player Card"
            ),
            emoji="👤",
            style=discord.ButtonStyle.success,
        )

        change_button = discord.ui.Button(
            label=(
                "تغيير الشخصية"
                if language == "ar"
                else "Change Character"
            ),
            emoji="🎭",
            style=discord.ButtonStyle.primary,
        )

        view_button.callback = self.show_card
        change_button.callback = self.change_character

        self.add_item(view_button)
        self.add_item(change_button)

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك."
                if self.language == "ar"
                else "This menu is not yours.",
            )

            return False

        return True

    async def show_card(
        self,
        interaction: discord.Interaction,
    ):

        if interaction.guild is None:
            await _send_private_error(
                interaction,
                "استخدمها داخل السيرفر."
                if self.language == "ar"
                else "Use this inside the server.",
            )
            return

        profile = get_player_profile(
            interaction.guild.id,
            interaction.user.id,
        )

        if profile is None:

            await _send_private_error(
                interaction,
                "لم تعد بطاقتك موجودة."
                if self.language == "ar"
                else "Your profile no longer exists.",
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        published = await publish_temporary_player_card(
            interaction.guild,
            interaction.user,
            profile,
            self.runtime,
        )

        if self.language == "ar":

            message = (
                "💜 تم نشر بطاقة لاعبك كصورة لمدة دقيقتين و30 ثانية."
                if published
                else "تعذر نشر البطاقة الآن، حاول مرة ثانية."
            )

        else:

            message = (
                "💜 Your PNG player card is public for 2 minutes and 30 seconds."
                if published
                else "Could not publish your card right now. Please try again."
            )

        await interaction.followup.send(
            message,
            ephemeral=True,
        )

    async def change_character(
        self,
        interaction: discord.Interaction,
    ):

        view = CharacterCategoryView(
            self.owner_id,
            self.language,
            self.runtime,
            mode="change",
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
                color=PURPLE,
            ),
            view=view,
        )


class NewPlayerCardView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        runtime,
    ):

        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.runtime = runtime

        self.add_item(
            LanguageButton(
                owner_id,
                "ar",
                runtime,
            )
        )

        self.add_item(
            LanguageButton(
                owner_id,
                "en",
                runtime,
            )
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك.",
            )

            return False

        return True


class LanguageButton(discord.ui.Button):

    def __init__(
        self,
        owner_id: int,
        language: str,
        runtime,
    ):

        self.owner_id = owner_id
        self.language = language
        self.runtime = runtime

        super().__init__(
            label=(
                "العربية"
                if language == "ar"
                else "English"
            ),
            emoji=(
                "🇸🇦"
                if language == "ar"
                else "🇬🇧"
            ),
            style=discord.ButtonStyle.primary,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        view = CharacterCategoryView(
            self.owner_id,
            self.language,
            self.runtime,
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
                color=PURPLE,
            ),
            view=view,
        )


class CharacterCategoryView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        language: str,
        runtime,
        mode: str = "create",
    ):

        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.language = language
        self.runtime = runtime
        self.mode = mode

        self.add_item(
            CharacterCategoryButton(
                owner_id,
                language,
                runtime,
                CATEGORY_ANIME,
                mode,
            )
        )

        self.add_item(
            CharacterCategoryButton(
                owner_id,
                language,
                runtime,
                CATEGORY_NETFLIX,
                mode,
            )
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك."
                if self.language == "ar"
                else "This menu is not yours.",
            )

            return False

        return True


class CharacterCategoryButton(discord.ui.Button):

    def __init__(
        self,
        owner_id: int,
        language: str,
        runtime,
        category: str,
        mode: str = "create",
    ):

        self.owner_id = owner_id
        self.language = language
        self.runtime = runtime
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
            style=discord.ButtonStyle.primary,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        characters = get_characters_by_category(
            self.category
        )

        options = []

        for item in characters[:25]:

            label = (
                item["name_ar"]
                if self.language == "ar"
                else item["name"]
            )

            series = item.get("series", "")

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=item["id"],
                    description=series[:100],
                )
            )

        view = CharacterChoiceView(
            self.owner_id,
            self.language,
            self.runtime,
            options,
            self.mode,
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
                color=PURPLE,
            ),
            view=view,
        )


class CharacterChoiceView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        language: str,
        runtime,
        options,
        mode: str = "create",
    ):

        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.language = language
        self.runtime = runtime
        self.mode = mode

        self.add_item(
            CharacterChoiceSelect(
                owner_id,
                language,
                runtime,
                options,
                mode,
            )
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await _send_private_error(
                interaction,
                "هذه القائمة ليست لك."
                if self.language == "ar"
                else "This menu is not yours.",
            )

            return False

        return True


class CharacterChoiceSelect(discord.ui.Select):

    def __init__(
        self,
        owner_id: int,
        language: str,
        runtime,
        options,
        mode: str = "create",
    ):

        self.owner_id = owner_id
        self.language = language
        self.runtime = runtime
        self.mode = mode

        super().__init__(
            placeholder=(
                "اختر شخصية"
                if language == "ar"
                else "Choose your character"
            ),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        character_id = self.values[0]
        character = get_character(character_id)

        if character is None:

            await _send_private_error(
                interaction,
                "الشخصية غير موجودة."
                if self.language == "ar"
                else "Character not found.",
            )

            return

        guild = interaction.guild

        if guild is None:

            await _send_private_error(
                interaction,
                "استخدمها داخل السيرفر."
                if self.language == "ar"
                else "Use this inside the server.",
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            if self.mode == "change":

                profile = get_player_profile(
                    guild.id,
                    interaction.user.id,
                )

                if profile is None:

                    await interaction.followup.send(
                        "بطاقتك غير موجودة، أنشئ بطاقة جديدة أولاً."
                        if self.language == "ar"
                        else "Your profile was not found. Please create a card first.",
                        ephemeral=True,
                    )

                    return

                # Preserve the saved V3 language and progression.
                save_player_profile(
                    guild.id,
                    interaction.user.id,
                    profile["profile_language"],
                    character_id,
                )

            else:

                # Create or update the V3 profile only.
                # No legacy V2 player/progress records are written.
                save_player_profile(
                    guild.id,
                    interaction.user.id,
                    self.language,
                    character_id,
                )

            profile = get_player_profile(
                guild.id,
                interaction.user.id,
            )

            published = await publish_temporary_player_card(
                guild,
                interaction.user,
                profile,
                self.runtime,
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

                except (
                    discord.Forbidden,
                    discord.HTTPException,
                ):

                    logger.info(
                        "Could not DM player-card confirmation to %s",
                        interaction.user.id,
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

            await interaction.followup.send(
                result_message,
                ephemeral=True,
            )

        except Exception:

            logger.exception(
                "V3 player-card workflow failed for %s",
                interaction.user.id,
            )

            error_message = (
                "تعذر إكمال العملية، حاول مرة ثانية."
                if self.language == "ar"
                else "Could not complete the action. Please try again."
            )

            await interaction.followup.send(
                error_message,
                ephemeral=True,
            )
