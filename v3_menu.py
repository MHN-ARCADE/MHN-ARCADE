
"""
MHN ARCADE V3 - Main Menu

Persistent Arabic and English main menus.
Games catalog is public.
Personal player interactions are private (ephemeral).
"""

from __future__ import annotations

import logging

import discord

from engine.achievements import ACHIEVEMENTS, TROPHY_TIERS
from characters import get_character
from database import get_selected_character

logger = logging.getLogger("mhn.arcade.v3.menu")

PURPLE = 0x7C3AED


# =========================================================
# MAIN MENU EMBEDS
# =========================================================

def create_main_menu_embed(
    language: str = "en",
) -> discord.Embed:

    if language == "ar":
        embed = discord.Embed(
            title="🎮 MHN ARCADE V3",
            description=(
                "مرحبًا بك في MHN ARCADE!\n"
                "اختر وش تبي تسوي من الخيارات اللي تحت."
            ),
            color=PURPLE,
        )

        embed.add_field(
            name="🎮 الألعاب",
            value="تصفح الألعاب واختر اللعبة اللي تبي تلعبها.",
            inline=False,
        )
        embed.add_field(
            name="👤 ملفي وإحصائياتي",
            value="شوف مستواك ورتبتك وإحصائياتك.",
            inline=False,
        )
        embed.add_field(
            name="🏆 التروفي",
            value="استعرض التروفيات اللي فتحتها واللي باقي لك.",
            inline=False,
        )
        embed.add_field(
            name="📊 لوحة المتصدرين",
            value="اعرف ترتيبك بين أعضاء السيرفر.",
            inline=False,
        )
        embed.set_footer(
            text="MHN ARCADE V3 • PLAY • COMPETE • WIN"
        )

    else:
        embed = discord.Embed(
            title="🎮 MHN ARCADE V3",
            description=(
                "Welcome to MHN ARCADE!\n"
                "Choose what you'd like to do below."
            ),
            color=PURPLE,
        )

        embed.add_field(
            name="🎮 Browse Games",
            value="Explore the game library and choose a game.",
            inline=False,
        )
        embed.add_field(
            name="👤 My Profile & Stats",
            value="View your level, rank, and gaming statistics.",
            inline=False,
        )
        embed.add_field(
            name="🏆 Trophy",
            value="View your unlocked and locked trophies.",
            inline=False,
        )
        embed.add_field(
            name="📊 Leaderboard",
            value="See your position among server members.",
            inline=False,
        )
        embed.set_footer(
            text="MHN ARCADE V3 • PLAY • COMPETE • WIN"
        )

    return embed


# =========================================================
# TROPHY COLLECTION EMBED
# =========================================================

def create_player_trophy_embed(
    stats: dict,
    language: str = "en",
) -> discord.Embed:
    """Builds the complete 18-trophy collection for one player."""

    unlocked_ids = {
        item["achievement_id"]
        for item in stats.get("achievements", [])
    }

    total_trophies = len(ACHIEVEMENTS)
    unlocked_count = len(
        unlocked_ids.intersection(ACHIEVEMENTS.keys())
    )

    if language == "ar":
        title = "🏆 مجموعة التروفيات"
        progress_text = (
            f"**تقدمك:** {unlocked_count}/{total_trophies} تروفي مفتوح\n"
            "اجمع التروفيات من خلال اللعب وتحقيق الشروط المطلوبة."
        )
    else:
        title = "🏆 Trophy Collection"
        progress_text = (
            f"**Your Progress:** {unlocked_count}/{total_trophies} trophies unlocked\n"
            "Play games and complete the requirements to collect them all."
        )

    embed = discord.Embed(
        title=title,
        description=progress_text,
        color=PURPLE,
    )

    tier_order = (
        "Common",
        "Uncommon",
        "Rare",
        "Very Rare",
        "Legendary",
        "Platinum",
    )

    for rarity in tier_order:

        tier = TROPHY_TIERS.get(rarity, {})

        tier_trophies = [
            (achievement_id, definition)
            for achievement_id, definition in ACHIEVEMENTS.items()
            if definition.get("rarity") == rarity
        ]

        if not tier_trophies:
            continue

        if language == "ar":
            tier_name = tier.get("name_ar", rarity)
            rank_name = tier.get("rank_ar", "")
            level_range = tier.get("level_range", "")
            field_name = (
                f"🏅 {tier_name} — {rank_name}"
            )
            level_label = "المستوى"
            required_label = "شرط الفتح"
            unlocked_label = "مفتوح"
            locked_label = "مقفول"
        else:
            tier_name = rarity
            rank_name = tier.get("rank_en", "")
            level_range = tier.get("level_range", "")
            field_name = (
                f"🏅 {tier_name} — {rank_name}"
            )
            level_label = "Level"
            required_label = "Requirement"
            unlocked_label = "Unlocked"
            locked_label = "Locked"

        lines = [
            f"**{level_label}: {level_range}**"
        ]

        for achievement_id, definition in tier_trophies:

            unlocked = achievement_id in unlocked_ids

            if language == "ar":
                trophy_name = definition["name_ar"]
                trophy_description = definition["description_ar"]
                status = (
                    f"✅ {unlocked_label}"
                    if unlocked
                    else f"🔒 {locked_label}"
                )
            else:
                trophy_name = definition["name_en"]
                trophy_description = definition["description_en"]
                status = (
                    f"✅ {unlocked_label}"
                    if unlocked
                    else f"🔒 {locked_label}"
                )

            minimum_level = int(
                definition.get("min_level", 1)
            )

            if language == "ar":
                requirement = (
                    f"المستوى {minimum_level}+"
                )
            else:
                requirement = (
                    f"Level {minimum_level}+"
                )

            lines.append(
                f"\n{status} **{trophy_name}**\n"
                f"{trophy_description}\n"
                f"<:blank:0> {required_label}: {requirement}"
            )

        embed.add_field(
            name=field_name,
            value="\n".join(lines),
            inline=False,
        )

    embed.set_footer(
        text="MHN ARCADE V3 • TROPHY COLLECTION"
    )

    return embed


# =========================================================
# MAIN MENU VIEW
# =========================================================

class V3MainMenuView(discord.ui.View):
    """Persistent main menu for Arabic or English channels."""

    def __init__(
        self,
        runtime,
        language: str = "en",
    ) -> None:

        super().__init__(timeout=None)

        self.runtime = runtime
        self.language = language

        if language == "ar":
            self.games_button.label = "الألعاب"
            self.profile_button.label = "ملفي وإحصائياتي"
            self.trophy_button.label = "التروفي"
            self.leaderboard_button.label = "لوحة المتصدرين"
        else:
            self.games_button.label = "Browse Games"
            self.profile_button.label = "My Profile & Stats"
            self.trophy_button.label = "Trophy"
            self.leaderboard_button.label = "Leaderboard"

        self.games_button.custom_id = (
            f"mhn:v3menu:{language}:games"
        )
        self.profile_button.custom_id = (
            f"mhn:v3menu:{language}:profile"
        )
        self.trophy_button.custom_id = (
            f"mhn:v3menu:{language}:trophy"
        )
        self.leaderboard_button.custom_id = (
            f"mhn:v3menu:{language}:leaderboard"
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.guild is None:
            await interaction.response.send_message(
                "This menu can only be used inside a server.",
                ephemeral=True,
            )
            return False

        return True

    # =====================================================
    # GAMES - PUBLIC FOR EVERYONE
    # =====================================================

    @discord.ui.button(
        label="Browse Games",
        emoji="🎮",
        style=discord.ButtonStyle.primary,
        custom_id="mhn:v3menu:en:games",
        row=0,
    )
    async def games_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        try:
            self.runtime.require_initialized()

            from v3_discord import (
                build_catalog_pages,
                CatalogView,
            )

            games = self.runtime.runner.list_games()

            pages = build_catalog_pages(
                games,
                self.language,
            )

            view = CatalogView(
                pages=pages,
                owner_id=None,
                language=self.language,
            )

            await interaction.response.send_message(
                embed=pages[0],
                view=view,
                ephemeral=False,
            )

            view.message = await interaction.original_response()

        except Exception:
            logger.exception("Main menu game catalog failed.")

            message = (
                "ما قدرنا نفتح قائمة الألعاب، حاول مرة ثانية."
                if self.language == "ar"
                else "Could not open the game library. Please try again."
            )

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

    # =====================================================
    # PROFILE - PRIVATE
    # =====================================================

    @discord.ui.button(
        label="My Profile & Stats",
        emoji="👤",
        style=discord.ButtonStyle.secondary,
        custom_id="mhn:v3menu:en:profile",
        row=0,
    )
    async def profile_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        try:
            self.runtime.require_initialized()

            member = interaction.user

            progress = await self.runtime.progression.get_player_progress(
                interaction.guild.id,
                member.id,
                member.display_name,
            )

            stats = await self.runtime.achievements.get_player_stats(
                member.id
            )

            level = progress["level"]
            total_xp = progress["total_xp"]
            current_xp = progress["xp"]
            next_level_xp = progress["xp_to_next_level"]
            rank = progress["rank"]

            games_played = progress["games_played"]
            wins = progress["wins"]
            losses = progress["losses"]
            draws = progress["draws"]

            multiplayer_games = stats["multiplayer_games"]
            trophies = len(stats["achievements"])

            if self.language == "ar":
                embed = discord.Embed(
                    title="👤 ملف اللاعب",
                    description=(
                        f"**اللاعب:** {member.mention}\n"
                        f"**الرتبة:** {rank}\n"
                        f"**المستوى:** {level}\n"
                        "إحصائياتك في MHN ARCADE V3"
                    ),
                    color=PURPLE,
                )

                embed.add_field(
                    name="⭐ مجموع XP",
                    value=f"{total_xp:,}",
                    inline=True,
                )
                embed.add_field(
                    name="📈 تقدم المستوى",
                    value=f"{current_xp:,} / {next_level_xp:,}",
                    inline=True,
                )
                embed.add_field(
                    name="🎮 الألعاب المكتملة",
                    value=str(games_played),
                    inline=True,
                )
                embed.add_field(
                    name="🏆 الانتصارات",
                    value=str(wins),
                    inline=True,
                )
                embed.add_field(
                    name="❌ الخسائر",
                    value=str(losses),
                    inline=True,
                )
                embed.add_field(
                    name="🤝 التعادلات",
                    value=str(draws),
                    inline=True,
                )
                embed.add_field(
                    name="👥 الألعاب الجماعية",
                    value=str(multiplayer_games),
                    inline=True,
                )
                embed.add_field(
                    name="💎 التروفيات المفتوحة",
                    value=str(trophies),
                    inline=True,
                )

            else:
                embed = discord.Embed(
                    title="👤 Player Profile",
                    description=(
                        f"**Player:** {member.mention}\n"
                        f"**Rank:** {rank}\n"
                        f"**Level:** {level}\n"
                        "Your MHN ARCADE V3 statistics."
                    ),
                    color=PURPLE,
                )

                embed.add_field(
                    name="⭐ Total XP",
                    value=f"{total_xp:,}",
                    inline=True,
                )
                embed.add_field(
                    name="📈 Level Progress",
                    value=f"{current_xp:,} / {next_level_xp:,}",
                    inline=True,
                )
                embed.add_field(
                    name="🎮 Games Completed",
                    value=str(games_played),
                    inline=True,
                )
                embed.add_field(
                    name="🏆 Wins",
                    value=str(wins),
                    inline=True,
                )
                embed.add_field(
                    name="❌ Losses",
                    value=str(losses),
                    inline=True,
                )
                embed.add_field(
                    name="🤝 Draws",
                    value=str(draws),
                    inline=True,
                )
                embed.add_field(
                    name="👥 Multiplayer Games",
                    value=str(multiplayer_games),
                    inline=True,
                )
                embed.add_field(
                    name="💎 Trophies Unlocked",
                    value=str(trophies),
                    inline=True,
                )

            selected = get_selected_character(
                interaction.guild.id,
                member.id
            )

            character = (
                get_character(selected["character_id"])
                if selected
                else None
            )

            if character and character.get("image_url"):
                embed.set_thumbnail(
                    url=character["image_url"]
                )

            embed.set_footer(
                text="MHN ARCADE V3"
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        except Exception:
            logger.exception("Main menu player profile failed.")

            message = (
                "ما قدرنا نعرض ملفك الحين، حاول مرة ثانية."
                if self.language == "ar"
                else "Could not load your profile. Please try again."
            )

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

    # =====================================================
    # TROPHIES - PRIVATE
    # =====================================================

    @discord.ui.button(
        label="Trophy",
        emoji="🏆",
        style=discord.ButtonStyle.secondary,
        custom_id="mhn:v3menu:en:trophy",
        row=1,
    )
    async def trophy_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        try:
            self.runtime.require_initialized()

            stats = await self.runtime.achievements.get_player_stats(
                interaction.user.id
            )

            embed = create_player_trophy_embed(
                stats=stats,
                language=self.language,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        except Exception:
            logger.exception("Main menu trophy display failed.")

            message = (
                "ما قدرنا نعرض التروفيات الحين، حاول مرة ثانية."
                if self.language == "ar"
                else "Could not load your trophies. Please try again."
            )

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

    # =====================================================
    # PERSONAL LEADERBOARD - PRIVATE
    # =====================================================

    @discord.ui.button(
        label="Leaderboard",
        emoji="📊",
        style=discord.ButtonStyle.success,
        custom_id="mhn:v3menu:en:leaderboard",
        row=1,
    )
    async def leaderboard_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        try:
            self.runtime.require_initialized()

            guild = interaction.guild

            # Include all cached human server members,
            # including members who have never earned XP.
            rankings = await self.runtime.progression.get_leaderboard(
                guild_id=guild.id,
                members=guild.members,
                limit=0,
            )

            if not rankings:
                message = (
                    "ما فيه أعضاء ظاهرين في لوحة الترتيب حاليًا."
                    if self.language == "ar"
                    else "There are no members available for the leaderboard."
                )

                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )
                return

            my_entry = next(
                (
                    item for item in rankings
                    if item["user_id"] == str(interaction.user.id)
                ),
                None,
            )

            if my_entry is None:
                message = (
                    "ما قدرنا نحدد ترتيبك حاليًا."
                    if self.language == "ar"
                    else "Your ranking could not be determined."
                )

                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )
                return

            top_players = rankings[:10]

            if self.language == "ar":
                lines = []

                for player in top_players:
                    medal = (
                        "🥇" if player["position"] == 1
                        else "🥈" if player["position"] == 2
                        else "🥉" if player["position"] == 3
                        else "🏅"
                    )

                    lines.append(
                        f"{medal} **#{player['position']} "
                        f"{discord.utils.escape_markdown(player['username'])}**"
                        f" — مستوى {player['level']} "
                        f"• {player['total_xp']:,} XP"
                    )

                description = "\n".join(lines)

                if my_entry["position"] > 10:
                    description += (
                        "\n\n━━━━━━━━━━━━━━\n"
                        f"👤 **ترتيبك:** #{my_entry['position']}\n"
                        f"**مستواك:** {my_entry['level']}\n"
                        f"**XP:** {my_entry['total_xp']:,}"
                    )
                else:
                    description += (
                        "\n\n━━━━━━━━━━━━━━\n"
                        f"💜 **ترتيبك الحالي: #{my_entry['position']}**"
                    )

                title = "📊 لوحة المتصدرين"

            else:
                lines = []

                for player in top_players:
                    medal = (
                        "🥇" if player["position"] == 1
                        else "🥈" if player["position"] == 2
                        else "🥉" if player["position"] == 3
                        else "🏅"
                    )

                    lines.append(
                        f"{medal} **#{player['position']} "
                        f"{discord.utils.escape_markdown(player['username'])}**"
                        f" — Level {player['level']} "
                        f"• {player['total_xp']:,} XP"
                    )

                description = "\n".join(lines)

                if my_entry["position"] > 10:
                    description += (
                        "\n\n━━━━━━━━━━━━━━\n"
                        f"👤 **Your Position:** #{my_entry['position']}\n"
                        f"**Your Level:** {my_entry['level']}\n"
                        f"**Your XP:** {my_entry['total_xp']:,}"
                    )
                else:
                    description += (
                        "\n\n━━━━━━━━━━━━━━\n"
                        f"💜 **Your Current Position: #{my_entry['position']}**"
                    )

                title = "📊 Leaderboard"

            embed = discord.Embed(
                title=title,
                description=description,
                color=PURPLE,
            )

            embed.set_thumbnail(
                url=guild.icon.url if guild.icon else interaction.user.display_avatar.url
            )

            embed.set_footer(
                text=(
                    f"MHN ARCADE V3 • {len(rankings)} members ranked"
                    if self.language != "ar"
                    else f"MHN ARCADE V3 • عدد الأعضاء: {len(rankings)}"
                )
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        except Exception:
            logger.exception("Main menu leaderboard failed.")

            message = (
                "ما قدرنا نعرض لوحة المتصدرين الحين، حاول مرة ثانية."
                if self.language == "ar"
                else "Could not load the leaderboard. Please try again."
            )

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
