
"""
MHN ARCADE V3 - Public Dashboards

Persistent dashboards:
- Combined Arabic/English leaderboard.
- Arabic top 10 leaderboard.
- English top 10 leaderboard.
- Bilingual trophy guide.
- Trophy completionists showcase.

All dashboards refresh automatically.
Existing saved messages are edited instead of duplicated.
"""

from __future__ import annotations

import logging
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from discord.ext import tasks

from engine.achievements import (
    ACHIEVEMENTS,
    TROPHY_TIERS,
)

from characters import get_character


logger = logging.getLogger("mhn.arcade.v3.dashboards")


# =========================================================
# CHANNELS
# =========================================================

LEADERBOARD_CHANNEL_ID = 1567720123106857142

ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910

ACHIEVEMENTS_CHANNEL_ID = 1567722630969303090


# =========================================================
# SETTINGS
# =========================================================

PURPLE = 0x7C3AED

DASHBOARD_REFRESH_SECONDS = 60

LEADERBOARD_LIMIT = 10
FINISHERS_PER_MESSAGE = 10

RECENT_ACHIEVEMENTS_LIMIT = 8

MEDALS = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
}


# =========================================================
# DASHBOARD MANAGER
# =========================================================

class V3DashboardManager:

    def __init__(
        self,
        bot: discord.Client,
        runtime: Any,
    ) -> None:

        self.bot = bot
        self.runtime = runtime

        self.db_path = Path(
            runtime.repository.db_path
        )

        self._initialized = False

    # =====================================================
    # DATABASE
    # =====================================================

    def _connect(self) -> sqlite3.Connection:

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        db = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        db.row_factory = sqlite3.Row

        db.execute(
            "PRAGMA busy_timeout = 30000"
        )

        return db

    def _initialize_database(self) -> None:

        with self._connect() as db:

            db.execute("""
                CREATE TABLE IF NOT EXISTS v3_dashboard_messages (
                    guild_id TEXT NOT NULL,
                    message_key TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    PRIMARY KEY (guild_id, message_key)
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS v3_dashboard_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    achievement_id TEXT NOT NULL,
                    name_ar TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    description_ar TEXT NOT NULL,
                    description_en TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL
                )
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS
                v3_dashboard_achievements_recent_idx
                ON v3_dashboard_achievements (
                    guild_id,
                    id DESC
                )
            """)

    # -----------------------------------------------------
    # SAVED MESSAGE STORAGE
    # -----------------------------------------------------

    def _get_saved_message(
        self,
        guild_id: int,
        message_key: str,
    ) -> dict[str, str] | None:

        with self._connect() as db:

            row = db.execute(
                """
                SELECT channel_id, message_id
                FROM v3_dashboard_messages
                WHERE guild_id = ?
                AND message_key = ?
                """,
                (
                    str(guild_id),
                    message_key,
                ),
            ).fetchone()

        return dict(row) if row else None

    def _save_message(
        self,
        guild_id: int,
        message_key: str,
        channel_id: int,
        message_id: int,
    ) -> None:

        with self._connect() as db:

            db.execute(
                """
                INSERT INTO v3_dashboard_messages (
                    guild_id,
                    message_key,
                    channel_id,
                    message_id
                )
                VALUES (?, ?, ?, ?)

                ON CONFLICT(guild_id, message_key)
                DO UPDATE SET
                    channel_id = excluded.channel_id,
                    message_id = excluded.message_id
                """,
                (
                    str(guild_id),
                    message_key,
                    str(channel_id),
                    str(message_id),
                ),
            )

    def _get_saved_page_keys(
        self,
        guild_id: int,
    ) -> list[str]:

        with self._connect() as db:

            rows = db.execute(
                """
                SELECT message_key
                FROM v3_dashboard_messages
                WHERE guild_id = ?
                AND message_key LIKE
                    'v3_trophy_finishers_page_%'
                """,
                (str(guild_id),),
            ).fetchall()

        return [
            str(row["message_key"])
            for row in rows
        ]

    def _delete_saved_message_record(
        self,
        guild_id: int,
        message_key: str,
    ) -> None:

        with self._connect() as db:

            db.execute(
                """
                DELETE FROM v3_dashboard_messages
                WHERE guild_id = ?
                AND message_key = ?
                """,
                (
                    str(guild_id),
                    message_key,
                ),
            )

    # =====================================================
    # CHANNEL HELPERS
    # =====================================================

    async def _get_text_channel(
        self,
        channel_id: int,
    ) -> discord.TextChannel | None:

        channel = self.bot.get_channel(
            channel_id
        )

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
                    "Could not fetch dashboard channel %s",
                    channel_id,
                )

                return None

        if not isinstance(
            channel,
            discord.TextChannel,
        ):

            logger.error(
                "Dashboard channel %s is not a text channel.",
                channel_id,
            )

            return None

        return channel

    # =====================================================
    # PERSISTENT MESSAGE HELPER
    # =====================================================

    async def _ensure_message(
        self,
        guild: discord.Guild,
        message_key: str,
        channel_id: int,
        embeds: list[discord.Embed],
    ) -> bool:

        if not embeds:
            return False

        if len(embeds) > 10:

            logger.error(
                "Message %s exceeds Discord's 10-embed limit.",
                message_key,
            )

            return False

        channel = await self._get_text_channel(
            channel_id
        )

        if (
            channel is None
            or channel.guild.id != guild.id
        ):
            return False

        saved = self._get_saved_message(
            guild.id,
            message_key,
        )

        if saved:

            try:

                old_channel = await self.bot.fetch_channel(
                    int(saved["channel_id"])
                )

                old_message = await old_channel.fetch_message(
                    int(saved["message_id"])
                )

                if old_channel.id == channel.id:

                    await old_message.edit(
                        content=None,
                        embeds=embeds,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )

                    return True

                await old_message.delete()

            except discord.NotFound:
                pass

            except (
                discord.Forbidden,
                discord.HTTPException,
            ):

                logger.exception(
                    "Could not update dashboard %s",
                    message_key,
                )

                return False

        try:

            message = await channel.send(
                embeds=embeds,
                allowed_mentions=discord.AllowedMentions.none(),
            )

            self._save_message(
                guild.id,
                message_key,
                channel.id,
                message.id,
            )

            return True

        except discord.HTTPException:

            logger.exception(
                "Could not create dashboard %s",
                message_key,
            )

            return False

    async def _delete_saved_message(
        self,
        guild: discord.Guild,
        message_key: str,
    ) -> None:

        saved = self._get_saved_message(
            guild.id,
            message_key,
        )

        if not saved:
            return

        try:

            channel = await self.bot.fetch_channel(
                int(saved["channel_id"])
            )

            message = await channel.fetch_message(
                int(saved["message_id"])
            )

            await message.delete()

        except discord.NotFound:
            pass

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):

            logger.exception(
                "Could not delete obsolete dashboard %s",
                message_key,
            )

            return

        self._delete_saved_message_record(
            guild.id,
            message_key,
        )

    # =====================================================
    # PLAYER CHARACTER AND IMAGE
    # =====================================================

    def _get_player_character(
        self,
        guild_id: int,
        user_id: str,
    ) -> dict[str, Any] | None:

        try:

            with self._connect() as db:

                row = db.execute(
                    """
                    SELECT character_id
                    FROM player_profiles
                    WHERE guild_id = ?
                    AND user_id = ?
                    """,
                    (
                        str(guild_id),
                        str(user_id),
                    ),
                ).fetchone()

            if row is None:
                return None

            return get_character(
                row["character_id"]
            )

        except sqlite3.Error:

            logger.exception(
                "Could not load character for player %s",
                user_id,
            )

            return None

    def _get_player_image(
        self,
        guild: discord.Guild,
        user_id: str,
        character: dict[str, Any] | None,
    ) -> str | None:

        # Prefer the selected character's image.
        if character:

            image_url = character.get(
                "image_url"
            )

            if image_url:
                return str(image_url)

        # Character catalog images are currently optional.
        # Use the player's Discord avatar as a safe fallback.
        member = guild.get_member(
            int(user_id)
        )

        if member is not None:
            return member.display_avatar.url

        return None

    # =====================================================
    # LEADERBOARD EMBEDS
    # =====================================================

    async def build_leaderboard_embeds(
        self,
        guild: discord.Guild,
        language: str = "both",
    ) -> list[discord.Embed]:

        players = await self.runtime.progression.get_leaderboard(
            guild_id=guild.id,
            members=None,
            limit=LEADERBOARD_LIMIT,
        )

        if not players:

            if language == "ar":

                title = "🏆 أقوى 10 لاعبين في MHN ARCADE"

                description = (
                    "يا هلا بالأبطال! 💜\n\n"
                    "ما عندنا ترتيب للحين.\n"
                    "ابدأ اللعب واجمع XP وخل اسمك بين الأوائل!"
                )

            elif language == "en":

                title = "🏆 MHN ARCADE — TOP 10"

                description = (
                    "Welcome, champions! 💜\n\n"
                    "There are no leaderboard results yet.\n"
                    "Start playing, earn XP, and claim your place!"
                )

            else:

                title = "🏆 MHN ARCADE — TOP 10"

                description = (
                    "ترتيب أقوى 10 لاعبين في السيرفر.\n"
                    "The server's top 10 strongest players.\n\n"
                    "ابدأ اللعب واجمع XP!\n"
                    "Play games and earn XP!"
                )

            embed = discord.Embed(
                title=title,
                description=description,
                color=PURPLE,
            )

            embed.set_footer(
                text="MHN ARCADE V3 • PLAY • COMPETE • WIN"
            )

            return [embed]

        embeds: list[discord.Embed] = []

        for player in players:

            position = int(
                player["position"]
            )

            user_id = str(
                player["user_id"]
            )

            username = str(
                player["username"]
            )

            rank = str(
                player["rank"]
            )

            level = int(
                player["level"]
            )

            total_xp = int(
                player["total_xp"]
            )

            wins = int(
                player["wins"]
            )

            games = int(
                player["games_played"]
            )

            medal = MEDALS.get(
                position,
                f"#{position}",
            )

            character = self._get_player_character(
                guild.id,
                user_id,
            )

            character_name_ar = (
                character.get("name_ar", "غير محددة")
                if character
                else "غير محددة"
            )

            character_name_en = (
                character.get("name", "Not selected")
                if character
                else "Not selected"
            )

            if language == "ar":

                embed = discord.Embed(
                    title=f"{medal} المركز {position} — {username[:70]}",
                    description=(
                        f"**الرتبة:** {rank}\n"
                        f"**المستوى:** {level}\n"
                        f"**الخبرة الكلية:** {total_xp:,} XP\n\n"
                        f"🏆 **عدد الانتصارات:** {wins:,}\n"
                        f"🎮 **الألعاب المكتملة:** {games:,}\n"
                        f"🎭 **الشخصية المختارة:** {character_name_ar}"
                    ),
                    color=PURPLE,
                )

                embed.set_footer(
                    text="MHN ARCADE V3 • أقوى 10 في السيرفر"
                )

            elif language == "en":

                embed = discord.Embed(
                    title=f"{medal} #{position} — {username[:70]}",
                    description=(
                        f"**Rank:** {rank}\n"
                        f"**Level:** {level}\n"
                        f"**Total XP:** {total_xp:,} XP\n\n"
                        f"🏆 **Wins:** {wins:,}\n"
                        f"🎮 **Completed Games:** {games:,}\n"
                        f"🎭 **Selected Character:** {character_name_en}"
                    ),
                    color=PURPLE,
                )

                embed.set_footer(
                    text="MHN ARCADE V3 • Server Top 10"
                )

            else:

                embed = discord.Embed(
                    title=f"{medal} #{position} — {username[:70]}",
                    description=(
                        f"⭐ **الرتبة | Rank:** {rank}\n"
                        f"📈 **المستوى | Level:** {level}\n"
                        f"✨ **XP الكلي | Total XP:** {total_xp:,}\n\n"
                        f"🏆 **الانتصارات | Wins:** {wins:,}\n"
                        f"🎮 **الألعاب | Games:** {games:,}\n"
                        f"🎭 **الشخصية | Character:** "
                        f"{character_name_ar} / {character_name_en}"
                    ),
                    color=PURPLE,
                )

                embed.set_footer(
                    text="MHN ARCADE V3 • PLAY • COMPETE • WIN"
                )

            image_url = self._get_player_image(
                guild,
                user_id,
                character,
            )

            if image_url:
                embed.set_thumbnail(
                    url=image_url
                )

            embeds.append(embed)

        return embeds[:10]

    # =====================================================
    # TROPHY REQUIREMENT TEXT
    # =====================================================

    @staticmethod
    def _get_requirement_text(
        achievement: dict[str, Any],
        language: str,
    ) -> str:

        requirements = []

        if achievement.get("games_required"):

            amount = achievement["games_required"]

            requirements.append(
                f"أكمل {amount} لعبة"
                if language == "ar"
                else f"Complete {amount} games"
            )

        if achievement.get("wins_required"):

            amount = achievement["wins_required"]

            requirements.append(
                f"حقق {amount} انتصار"
                if language == "ar"
                else f"Earn {amount} wins"
            )

        if achievement.get("multiplayer_required"):

            amount = achievement["multiplayer_required"]

            requirements.append(
                f"شارك في {amount} لعبة جماعية"
                if language == "ar"
                else f"Join {amount} multiplayer games"
            )

        if achievement.get("game_types_required"):

            amount = achievement["game_types_required"]

            requirements.append(
                f"حقق انتصارات في {amount} أنواع ألعاب مختلفة"
                if language == "ar"
                else f"Win across {amount} different game types"
            )

        if not requirements:

            return (
                "متطلبات خاصة"
                if language == "ar"
                else "Special requirements"
            )

        return " + ".join(requirements)

    # =====================================================
    # TROPHY GUIDE
    # =====================================================

    def build_trophy_guide_embeds(
        self,
    ) -> list[discord.Embed]:

        embed = discord.Embed(
            title="🏆 دليل التروفيات | MHN ARCADE",
            description=(
                "اجمع الكؤوس، ارفع مستواك، واثبت إنك من أبطال الأركيد! 💜\n"
                "Collect trophies, level up, and prove your place among the champions!\n\n"
                "**مستوى اللاعب المطلوب يحدد إمكانية فتح الكأس، "
                "ولازم تحقق شرط اللعب بعد.**\n"
                "**Your level unlocks the trophy tier, and you must also meet its gameplay requirement.**"
            ),
            color=PURPLE,
        )

        tier_order = [
            "Common",
            "Uncommon",
            "Rare",
            "Very Rare",
            "Legendary",
            "Platinum",
        ]

        for tier_name in tier_order:

            tier = TROPHY_TIERS[tier_name]

            if tier_name == "Common":
                tier_emoji = "⚪"
            elif tier_name == "Uncommon":
                tier_emoji = "🟢"
            elif tier_name == "Rare":
                tier_emoji = "🔵"
            elif tier_name == "Very Rare":
                tier_emoji = "🟣"
            elif tier_name == "Legendary":
                tier_emoji = "🟠"
            else:
                tier_emoji = "💎"

            tier_trophies = [
                (achievement_id, item)
                for achievement_id, item in ACHIEVEMENTS.items()
                if item["rarity"] == tier_name
            ]

            tier_header = (
                f"{tier_emoji} {tier_name} "
                f"• {tier['name_ar']}"
            )

            tier_lines = [
                (
                    f"**المستوى | Level:** {tier['level_range']}\n"
                    f"**الرتبة | Rank:** {tier['rank_ar']} "
                    f"/ {tier['rank_en']}"
                )
            ]

            for achievement_id, item in tier_trophies:

                min_level = int(
                    item.get("min_level", 1)
                )

                requirement_ar = self._get_requirement_text(
                    item,
                    "ar",
                )

                requirement_en = self._get_requirement_text(
                    item,
                    "en",
                )

                tier_lines.append(
                    f"\n**🏅 {item['name_ar']} | {item['name_en']}**\n"
                    f"{item['description_ar']}\n"
                    f"{item['description_en']}\n"
                    f"🔓 المستوى المطلوب: **{min_level}+** "
                    f"| Required level: **{min_level}+**\n"
                    f"📌 {requirement_ar}\n"
                    f"📌 {requirement_en}"
                )

            embed.add_field(
                name=tier_header,
                value="\n".join(tier_lines)[:1024],
                inline=False,
            )

        embed.set_footer(
            text=(
                f"MHN ARCADE V3 • {len(ACHIEVEMENTS)} TROPHIES "
                "• PLAY • COMPETE • WIN"
            )
        )

        return [embed]

    # =====================================================
    # TROPHY COMPLETIONISTS
    # =====================================================

    def _get_completionists(
        self,
        guild_id: int,
    ) -> list[dict[str, Any]]:

        with self._connect() as db:

            rows = db.execute(
                """
                SELECT
                    a.user_id,
                    p.username,
                    p.total_xp,
                    p.games_played,
                    p.wins,
                    COUNT(DISTINCT a.achievement_id) AS trophy_count

                FROM v3_player_achievements AS a

                INNER JOIN v3_player_progress AS p
                    ON p.user_id = a.user_id
                    AND p.guild_id = ?

                WHERE a.user_id IN (
                    SELECT user_id
                    FROM v3_player_achievements
                    GROUP BY user_id
                    HAVING COUNT(DISTINCT achievement_id) >= ?
                )

                GROUP BY
                    a.user_id,
                    p.username,
                    p.total_xp,
                    p.games_played,
                    p.wins

                ORDER BY
                    p.total_xp DESC,
                    p.wins DESC,
                    p.games_played DESC
                """,
                (
                    str(guild_id),
                    len(ACHIEVEMENTS),
                ),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    async def build_trophy_finisher_embeds(
        self,
        guild: discord.Guild,
    ) -> list[discord.Embed]:

        players = self._get_completionists(
            guild.id
        )

        if not players:

            embed = discord.Embed(
                title="💎 ختم التروفيات | Trophy Completionists",
                description=(
                    "ما عندنا لاعب جمع كل التروفيات للحين.\n"
                    "أول لاعب يكمل المجموعة كاملة بيكون اسمه هنا! 💜\n\n"
                    "No player has collected every trophy yet.\n"
                    "The first player to complete the full collection will be featured here!"
                ),
                color=PURPLE,
            )

            embed.set_footer(
                text="MHN ARCADE V3 • COMPLETE THE COLLECTION"
            )

            return [embed]

        embeds: list[discord.Embed] = []

        for position, player in enumerate(
            players,
            start=1,
        ):

            user_id = str(
                player["user_id"]
            )

            username = str(
                player["username"]
            )

            progress = await self.runtime.progression.get_player_progress(
                guild_id=guild.id,
                user_id=user_id,
                username=username,
            )

            level = int(
                progress.get("level", 1)
            )

            rank = str(
                progress.get("rank", "ROOKIE")
            )

            total_xp = int(
                progress.get("total_xp", 0)
            )

            character = self._get_player_character(
                guild.id,
                user_id,
            )

            character_name_ar = (
                character.get("name_ar", "غير محددة")
                if character
                else "غير محددة"
            )

            character_name_en = (
                character.get("name", "Not selected")
                if character
                else "Not selected"
            )

            embed = discord.Embed(
                title=f"💎 #{position} — {username[:70]}",
                description=(
                    f"🏆 **التروفيات المكتملة:** "
                    f"{len(ACHIEVEMENTS)}/{len(ACHIEVEMENTS)}\n"
                    f"📈 **المستوى | Level:** {level}\n"
                    f"⭐ **الرتبة | Rank:** {rank}\n"
                    f"✨ **إجمالي الخبرة | Total XP:** {total_xp:,}\n\n"
                    f"🎭 **الشخصية المختارة:** {character_name_ar}\n"
                    f"🎭 **Selected Character:** {character_name_en}"
                ),
                color=PURPLE,
            )

            image_url = self._get_player_image(
                guild,
                user_id,
                character,
            )

            if image_url:
                embed.set_thumbnail(
                    url=image_url
                )

            embed.set_footer(
                text="MHN ARCADE V3 • TROPHY COMPLETIONIST"
            )

            embeds.append(embed)

        return embeds

    # =====================================================
    # RECENT TROPHY UNLOCKS
    # =====================================================

    def _get_recent_achievements(
        self,
        guild_id: int,
    ) -> list[dict[str, Any]]:

        with self._connect() as db:

            rows = db.execute(
                """
                SELECT *
                FROM v3_dashboard_achievements
                WHERE guild_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    str(guild_id),
                    RECENT_ACHIEVEMENTS_LIMIT,
                ),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    # =====================================================
    # TROPHY EVENT STORAGE
    # =====================================================

    async def on_achievements_unlocked(
        self,
        unlocked: list[dict[str, str]],
    ) -> None:

        if not unlocked:
            return

        for item in unlocked:

            user_id = str(
                item["user_id"]
            )

            matching_guilds = [
                guild
                for guild in self.bot.guilds
                if guild.get_member(int(user_id)) is not None
            ]

            if not matching_guilds:
                matching_guilds = list(
                    self.bot.guilds
                )

            for guild in matching_guilds:

                try:

                    with self._connect() as db:

                        db.execute(
                            """
                            INSERT INTO v3_dashboard_achievements (
                                guild_id,
                                user_id,
                                username,
                                achievement_id,
                                name_ar,
                                name_en,
                                description_ar,
                                description_en,
                                rarity,
                                unlocked_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                str(guild.id),
                                user_id,
                                str(item["username"]),
                                str(item["achievement_id"]),
                                str(item["name_ar"]),
                                str(item["name_en"]),
                                str(item["description_ar"]),
                                str(item["description_en"]),
                                str(item["rarity"]),
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )

                except Exception:

                    logger.exception(
                        "Could not save trophy unlock event."
                    )

        await self.refresh_all()

    # =====================================================
    # REFRESH LEADERBOARDS
    # =====================================================

    async def _refresh_leaderboards(
        self,
        guild: discord.Guild,
    ) -> None:

        # Keep the unified leaderboard only in the dedicated channel.
        combined = await self.build_leaderboard_embeds(
            guild,
            language="both",
        )

        await self._ensure_message(
            guild,
            "v3_leaderboard",
            LEADERBOARD_CHANNEL_ID,
            combined,
        )

        # Remove the old Arabic and English leaderboard messages
        # from the arcade channels and clear their saved records.
        await self._delete_saved_message(
            guild,
            "v3_leaderboard_ar",
        )

        await self._delete_saved_message(
            guild,
            "v3_leaderboard_en",
        )

    # =====================================================
    # REFRESH TROPHY GUIDE
    # =====================================================

    async def _refresh_trophy_guide(
        self,
        guild: discord.Guild,
    ) -> None:

        guide = self.build_trophy_guide_embeds()

        await self._ensure_message(
            guild,
            "v3_achievements",
            ACHIEVEMENTS_CHANNEL_ID,
            guide,
        )

    # =====================================================
    # REFRESH COMPLETIONISTS
    # =====================================================

    async def _refresh_trophy_finishers(
        self,
        guild: discord.Guild,
    ) -> None:

        embeds = await self.build_trophy_finisher_embeds(
            guild
        )

        # Discord allows up to 10 embeds in one message.
        # If more players complete every trophy, the
        # showcase automatically continues in page messages.

        pages = [
            embeds[index:index + FINISHERS_PER_MESSAGE]
            for index in range(
                0,
                len(embeds),
                FINISHERS_PER_MESSAGE,
            )
        ]

        if not pages:
            pages = [[]]

        active_keys = set()

        for page_number, page_embeds in enumerate(
            pages,
            start=1,
        ):

            message_key = (
                f"v3_trophy_finishers_page_{page_number}"
            )

            active_keys.add(
                message_key
            )

            if not page_embeds:
                continue

            await self._ensure_message(
                guild,
                message_key,
                ACHIEVEMENTS_CHANNEL_ID,
                page_embeds,
            )

        # Remove outdated pages if the number of finishers drops.
        for old_key in self._get_saved_page_keys(
            guild.id
        ):

            if old_key not in active_keys:

                await self._delete_saved_message(
                    guild,
                    old_key,
                )

    # =====================================================
    # REFRESH ALL DASHBOARDS
    # =====================================================

    async def refresh_guild(
        self,
        guild: discord.Guild,
    ) -> None:

        try:

            await self._refresh_leaderboards(
                guild
            )

            await self._refresh_trophy_guide(
                guild
            )

            await self._refresh_trophy_finishers(
                guild
            )

        except Exception:

            logger.exception(
                "Could not refresh V3 dashboards for %s",
                guild.name,
            )

    async def refresh_all(self) -> None:

        for guild in self.bot.guilds:

            await self.refresh_guild(
                guild
            )

    # =====================================================
    # AUTOMATIC UPDATES
    # =====================================================

    @tasks.loop(
        seconds=DASHBOARD_REFRESH_SECONDS
    )
    async def refresh_loop(self) -> None:

        await self.refresh_all()

    @refresh_loop.before_loop
    async def before_refresh_loop(self) -> None:

        await self.bot.wait_until_ready()

    # =====================================================
    # START
    # =====================================================

    async def initialize(self) -> None:

        if self._initialized:

            await self.refresh_all()
            return

        self._initialize_database()

        self.runtime.achievement_announcement_callback = (
            self.on_achievements_unlocked
        )

        await self.refresh_all()

        if not self.refresh_loop.is_running():

            self.refresh_loop.start()

        self._initialized = True

        logger.info(
            "V3 leaderboards and trophy dashboards initialized."
        )

    # =====================================================
    # SHUTDOWN
    # =====================================================

    async def shutdown(self) -> None:

        if self.refresh_loop.is_running():

            self.refresh_loop.cancel()

        self._initialized = False
