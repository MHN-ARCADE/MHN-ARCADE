
"""
MHN ARCADE V3 - Public Dashboards

Maintains one persistent leaderboard panel and one
persistent achievements panel per Discord server.
"""

from __future__ import annotations

import logging
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from discord.ext import tasks

from engine.achievements import ACHIEVEMENTS


logger = logging.getLogger("mhn.arcade.v3.dashboards")

LEADERBOARD_CHANNEL_ID = 1567720123106857142
ACHIEVEMENTS_CHANNEL_ID = 1567722630969303090

PURPLE = 0x7C3AED
DASHBOARD_REFRESH_SECONDS = 60
RECENT_ACHIEVEMENTS_LIMIT = 8


class V3DashboardManager:

    def __init__(
        self,
        bot: discord.Client,
        runtime: Any,
    ) -> None:

        self.bot = bot
        self.runtime = runtime
        self.db_path = Path(runtime.repository.db_path)
        self._initialized = False

    # ==================================================
    # DATABASE
    # ==================================================

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
        db.execute("PRAGMA busy_timeout = 30000")

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
                WHERE guild_id = ? AND message_key = ?
                """,
                (str(guild_id), message_key),
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

    # ==================================================
    # CHANNEL AND MESSAGE HELPERS
    # ==================================================

    async def _get_text_channel(
        self,
        channel_id: int,
    ) -> discord.TextChannel | None:

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
                    "Could not fetch dashboard channel %s",
                    channel_id,
                )

                return None

        if not isinstance(channel, discord.TextChannel):
            logger.error(
                "Dashboard channel %s is not a text channel.",
                channel_id,
            )
            return None

        return channel

    async def _ensure_message(
        self,
        guild: discord.Guild,
        message_key: str,
        channel_id: int,
        embed: discord.Embed,
    ) -> bool:

        channel = await self._get_text_channel(channel_id)

        if channel is None or channel.guild.id != guild.id:
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
                        embed=embed,
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
                embed=embed,
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

    # ==================================================
    # LEADERBOARD
    # ==================================================

    async def build_leaderboard_embed(
        self,
        guild: discord.Guild,
    ) -> discord.Embed:

        players = await self.runtime.progression.get_leaderboard(
            guild_id=guild.id,
            members=None,
            limit=10,
        )

        embed = discord.Embed(
            title="🏆 MHN ARCADE V3 — LEADERBOARD",
            description=(
                "أفضل 10 لاعبين في الأركيد\n"
                "Top 10 players ranked by XP\n\n"
                "📊 الترتيب يعتمد على XP ثم الانتصارات."
            ),
            color=PURPLE,
        )

        if not players:

            embed.description += (
                "\n\n🎮 لا توجد نتائج حتى الآن.\n"
                "ابدأ اللعب لتظهر هنا!"
            )

        else:

            medals = {
                1: "🥇",
                2: "🥈",
                3: "🥉",
            }

            for player in players:

                position = int(player["position"])
                medal = medals.get(position, f"`#{position}`")

                value = (
                    f"⭐ **{player['rank']}**"
                    f"  •  Level **{player['level']}**\n"
                    f"✨ XP: **{player['total_xp']:,}**\n"
                    f"🎮 Games: **{player['games_played']}**"
                    f"  •  🏆 Wins: **{player['wins']}**\n"
                    f"❌ Losses: **{player['losses']}**"
                    f"  •  🤝 Draws: **{player['draws']}**"
                )

                embed.add_field(
                    name=(
                        f"{medal} "
                        f"{str(player['username'])[:70]}"
                    ),
                    value=value,
                    inline=False,
                )

        embed.set_footer(
            text="MHN ARCADE V3 • PLAY • COMPETE • WIN"
        )

        return embed

    # ==================================================
    # ACHIEVEMENTS
    # ==================================================

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

        return [dict(row) for row in rows]

    async def build_achievements_embed(
        self,
        guild: discord.Guild,
    ) -> discord.Embed:

        embed = discord.Embed(
            title="🏆 MHN ARCADE V3 — ACHIEVEMENTS",
            description=(
                "افتح الإنجازات وأثبت مهارتك في الأركيد!\n"
                "Unlock achievements and build your legacy!\n\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            color=PURPLE,
        )

        for achievement in ACHIEVEMENTS.values():

            name = (
                f"{achievement['name_ar']} "
                f"• {achievement['name_en']}"
            )

            description = (
                f"{achievement['description_ar']}\n"
                f"{achievement['description_en']}\n"
                f"⭐ Rarity: **{achievement['rarity']}**"
            )

            embed.add_field(
                name=f"💎 {name}",
                value=description,
                inline=False,
            )

        recent = self._get_recent_achievements(guild.id)

        if recent:

            recent_lines = []

            for item in recent:

                recent_lines.append(
                    f"🏅 <@{item['user_id']}> "
                    f"— **{item['name_en']}**"
                )

            recent_text = "\n".join(recent_lines)

        else:

            recent_text = (
                "لا توجد إنجازات مفتوحة حتى الآن.\n"
                "No achievements unlocked yet."
            )

        embed.add_field(
            name="🔥 Latest Unlocks | آخر الإنجازات",
            value=recent_text[:1024],
            inline=False,
        )

        embed.set_footer(
            text="MHN ARCADE V3 • Every achievement tells a story"
        )

        return embed

    # ==================================================
    # REFRESH DASHBOARDS
    # ==================================================

    async def refresh_guild(
        self,
        guild: discord.Guild,
    ) -> None:

        try:

            leaderboard = await self.build_leaderboard_embed(
                guild
            )

            await self._ensure_message(
                guild,
                "v3_leaderboard",
                LEADERBOARD_CHANNEL_ID,
                leaderboard,
            )

            achievements = await self.build_achievements_embed(
                guild
            )

            await self._ensure_message(
                guild,
                "v3_achievements",
                ACHIEVEMENTS_CHANNEL_ID,
                achievements,
            )

        except Exception:

            logger.exception(
                "Could not refresh V3 dashboards for %s",
                guild.name,
            )

    async def refresh_all(self) -> None:

        for guild in self.bot.guilds:
            await self.refresh_guild(guild)

    # ==================================================
    # ACHIEVEMENT UNLOCK CALLBACK
    # ==================================================

    async def on_achievements_unlocked(
        self,
        unlocked: list[dict[str, str]],
    ) -> None:

        if not unlocked:
            return

        for item in unlocked:

            user_id = str(item["user_id"])

            matching_guilds = [
                guild
                for guild in self.bot.guilds
                if guild.get_member(int(user_id)) is not None
            ]

            # If the member is not cached, use the bot's
            # available guilds as a fallback.
            if not matching_guilds:
                matching_guilds = list(self.bot.guilds)

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
                        "Could not save achievement dashboard event."
                    )

        await self.refresh_all()

    # ==================================================
    # AUTOMATIC UPDATES
    # ==================================================

    @tasks.loop(seconds=DASHBOARD_REFRESH_SECONDS)
    async def refresh_loop(self) -> None:

        await self.refresh_all()

    @refresh_loop.before_loop
    async def before_refresh_loop(self) -> None:

        await self.bot.wait_until_ready()

    # ==================================================
    # START
    # ==================================================

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
            "V3 leaderboard and achievements dashboards initialized."
        )

    async def shutdown(self) -> None:

        if self.refresh_loop.is_running():
            self.refresh_loop.cancel()

        self._initialized = False
