
"""
========================================================
MHN ARCADE V2.0
Interactive Games Engine
30 Playable Mini-Games 💜
========================================================

Dependencies:
    discord.py == 2.7.1

Database functions required:
    record_game_result
    get_player

Integration:
    await bot.add_cog(ArcadeGames(bot))
========================================================
"""

import random
import time
import logging

import discord
from discord.ext import commands
from discord import app_commands

from database import record_game_result, get_player


logger = logging.getLogger("mhn.arcade.games")

PURPLE = 0x7C3AED
COOLDOWN_SECONDS = 8

# ========================================================
# GAME CATALOG
# ========================================================

CATEGORIES = {
    "social": {
        "name": "Social & Competition",
        "name_ar": "المنافسة والتحديات",
        "emoji": "🏆",
        "games": [
            "musical_chairs",
            "roulette",
            "mafia",
            "impostor",
            "hide_seek",
            "dice_battle",
            "rps",
            "guess_who",
        ],
    },
    "speed": {
        "name": "Speed & Reflex",
        "name_ar": "السرعة وردة الفعل",
        "emoji": "⚡",
        "games": [
            "fast_click",
            "fast_type",
            "text_split",
            "unscramble",
            "find_emoji",
            "color_match",
            "sort_numbers",
        ],
    },
    "brain": {
        "name": "Brain & Puzzle",
        "name_ar": "الذكاء والألغاز",
        "emoji": "🧠",
        "games": [
            "memory",
            "trivia",
            "riddles",
            "guess_character",
            "guess_anime",
            "guess_flag",
            "hangman",
            "wordle",
        ],
    },
    "luck": {
        "name": "Luck & Strategy",
        "name_ar": "الحظ والاستراتيجية",
        "emoji": "🎲",
        "games": [
            "tic_tac_toe",
            "connect_four",
            "minesweeper",
            "bank_manager",
            "coin_flip",
            "slots",
            "safe_trap",
        ],
    },
}


# Each challenge has:
# English question, Arabic question, options, answer index.

GAMES = {

    # ----------------------------------------------------
    # SOCIAL & COMPETITION
    # ----------------------------------------------------

    "musical_chairs": {
        "name": "Musical Chairs",
        "name_ar": "الكراسي الموسيقية",
        "emoji": "🪑",
        "questions": [
            ("The music stopped! Which chair is free?",
             "توقفت الموسيقى! أي كرسي ما زال متاحًا؟",
             ["Chair 1", "Chair 2", "Chair 3", "Chair 4"], 2),
        ],
    },

    "roulette": {
        "name": "Elimination Roulette",
        "name_ar": "روليت الإقصاء",
        "emoji": "🎯",
        "questions": [
            ("Choose the safe number!",
             "اختر الرقم الآمن!",
             ["1", "2", "3", "4"], 1),
        ],
    },

    "mafia": {
        "name": "Mafia",
        "name_ar": "المافيا",
        "emoji": "🕵️",
        "questions": [
            ("A player is acting suspiciously. What should you do?",
             "أحد اللاعبين يتصرف بريبة. ماذا تفعل؟",
             ["Investigate", "Ignore", "Leave", "Sleep"], 0),
        ],
    },

    "impostor": {
        "name": "Impostor",
        "name_ar": "المحتال",
        "emoji": "🎭",
        "questions": [
            ("Find the word that does not belong!",
             "اكتشف الكلمة المختلفة!",
             ["Apple", "Banana", "Car", "Orange"], 2),
        ],
    },

    "hide_seek": {
        "name": "Hide & Seek",
        "name_ar": "الغميضة",
        "emoji": "🙈",
        "questions": [
            ("Where would you hide?",
             "أين ستختبئ؟",
             ["Behind the door", "Under the table",
              "Inside the closet", "Behind the sofa"], 2),
        ],
    },

    "dice_battle": {
        "name": "Dice Battle",
        "name_ar": "معركة النرد",
        "emoji": "🎲",
        "questions": [
            ("Which dice result is the highest?",
             "أي نتيجة نرد هي الأعلى؟",
             ["2", "4", "6", "3"], 2),
        ],
    },

    "rps": {
        "name": "Rock Paper Scissors",
        "name_ar": "حجر ورقة مقص",
        "emoji": "✊",
        "questions": [
            ("What beats Rock?",
             "ما الذي يهزم الحجر؟",
             ["Rock", "Paper", "Scissors", "Nothing"], 1),
        ],
    },

    "guess_who": {
        "name": "Guess Who",
        "name_ar": "من أنا؟",
        "emoji": "❓",
        "questions": [
            ("I have four legs and bark. Who am I?",
             "لدي أربع أرجل وأنبح. من أنا؟",
             ["Cat", "Dog", "Bird", "Fish"], 1),
        ],
    },


    # ----------------------------------------------------
    # SPEED & REFLEX
    # ----------------------------------------------------

    "fast_click": {
        "name": "Fast Click",
        "name_ar": "النقرة السريعة",
        "emoji": "⚡",
        "questions": [
            ("Click the correct answer as fast as possible!",
             "اختر الإجابة الصحيحة بأسرع وقت!",
             ["FAST", "SLOW", "WAIT", "STOP"], 0),
        ],
    },

    "fast_type": {
        "name": "Fast Type",
        "name_ar": "الكتابة السريعة",
        "emoji": "⌨️",
        "questions": [
            ("Which word matches the target: ARCADE?",
             "أي كلمة تطابق الكلمة المطلوبة: ARCADE؟",
             ["ARCADE", "ARCAD", "ARCADEE", "ARC"], 0),
        ],
    },

    "text_split": {
        "name": "Text Split",
        "name_ar": "ترتيب النص",
        "emoji": "🔤",
        "questions": [
            ("Which is the correct spelling?",
             "ما التهجئة الصحيحة؟",
             ["GAMMING", "GAMING", "GAMIN", "GAMMNG"], 1),
        ],
    },

    "unscramble": {
        "name": "Unscramble",
        "name_ar": "فك الحروف",
        "emoji": "🔠",
        "questions": [
            ("Unscramble: YALP",
             "رتب الحروف: YALP",
             ["PLAY", "PAYL", "PALY", "PYAL"], 0),
        ],
    },

    "find_emoji": {
        "name": "Find Emoji",
        "name_ar": "اكتشف الإيموجي",
        "emoji": "🔎",
        "questions": [
            ("Find the controller!",
             "اعثر على يد التحكم!",
             ["🎮", "🎲", "🎯", "🎧"], 0),
        ],
    },

    "color_match": {
        "name": "Color Match",
        "name_ar": "مطابقة الألوان",
        "emoji": "🎨",
        "questions": [
            ("Which option is the color BLUE?",
             "أي خيار يمثل اللون الأزرق؟",
             ["🔴 Red", "🔵 Blue", "🟢 Green", "🟡 Yellow"], 1),
        ],
    },

    "sort_numbers": {
        "name": "Sort Numbers",
        "name_ar": "ترتيب الأرقام",
        "emoji": "🔢",
        "questions": [
            ("Which number is the smallest?",
             "ما الرقم الأصغر؟",
             ["19", "7", "12", "25"], 1),
        ],
    },


    # ----------------------------------------------------
    # BRAIN & PUZZLE
    # ----------------------------------------------------

    "memory": {
        "name": "Memory",
        "name_ar": "الذاكرة",
        "emoji": "🧩",
        "questions": [
            ("Which sequence contains the number 7?",
             "أي تسلسل يحتوي على الرقم 7؟",
             ["12345", "24680", "13792", "45601"], 2),
        ],
    },

    "trivia": {
        "name": "Trivia",
        "name_ar": "المعلومات العامة",
        "emoji": "📚",
        "questions": [
            ("What is the largest planet in our solar system?",
             "ما أكبر كوكب في مجموعتنا الشمسية؟",
             ["Earth", "Mars", "Jupiter", "Venus"], 2),
        ],
    },

    "riddles": {
        "name": "Riddles",
        "name_ar": "الألغاز",
        "emoji": "💡",
        "questions": [
            ("What has keys but cannot open locks?",
             "ما الشيء الذي له مفاتيح ولا يفتح الأقفال؟",
             ["A Piano", "A Door", "A Box", "A Clock"], 0),
        ],
    },

    "guess_character": {
        "name": "Guess the Character",
        "name_ar": "خمن الشخصية",
        "emoji": "🎬",
        "questions": [
            ("Which character is known as the King of Curses?",
             "من الشخصية المعروفة بلقب ملك اللعنات؟",
             ["Gojo", "Sukuna", "Levi", "Ichigo"], 1),
        ],
    },

    "guess_anime": {
        "name": "Guess Anime",
        "name_ar": "خمن الأنمي",
        "emoji": "⛩️",
        "questions": [
            ("In which anime is the character Levi?",
             "في أي أنمي تظهر شخصية ليفاي؟",
             ["Naruto", "Bleach", "Attack on Titan",
              "One Piece"], 2),
        ],
    },

    "guess_flag": {
        "name": "Guess the Flag",
        "name_ar": "خمن العلم",
        "emoji": "🌍",
        "questions": [
            ("Which country has a red circle on a white flag?",
             "أي دولة علمها دائرة حمراء على خلفية بيضاء؟",
             ["Japan", "Canada", "Turkey", "France"], 0),
        ],
    },

    "hangman": {
        "name": "Hangman",
        "name_ar": "الرجل المشنوق",
        "emoji": "🔡",
        "questions": [
            ("Which word completes: G _ M E?",
             "ما الكلمة التي تكمل: G _ M E؟",
             ["GAME", "GOME", "GIME", "GUME"], 0),
        ],
    },

    "wordle": {
        "name": "Wordle",
        "name_ar": "ووردل",
        "emoji": "🟩",
        "questions": [
            ("Choose the correct five-letter gaming word.",
             "اختر كلمة ألعاب صحيحة من خمسة أحرف.",
             ["LEVEL", "LEVLE", "LEVE", "LEVAL"], 0),
        ],
    },


    # ----------------------------------------------------
    # LUCK & STRATEGY
    # ----------------------------------------------------

    "tic_tac_toe": {
        "name": "Tic Tac Toe",
        "name_ar": "إكس أو",
        "emoji": "⭕",
        "questions": [
            ("Which symbol is traditionally used by the first player?",
             "ما الرمز الذي يستخدمه اللاعب الأول عادة؟",
             ["X", "O", "△", "□"], 0),
        ],
    },

    "connect_four": {
        "name": "Connect Four",
        "name_ar": "أربع على التوالي",
        "emoji": "🔴",
        "questions": [
            ("How many pieces must you connect to win?",
             "كم قطعة تحتاج لتوصيلها للفوز؟",
             ["2", "3", "4", "5"], 2),
        ],
    },

    "minesweeper": {
        "name": "Minesweeper",
        "name_ar": "كاسح الألغام",
        "emoji": "💣",
        "questions": [
            ("What does a number 1 indicate in Minesweeper?",
             "ماذا يعني الرقم 1 في كاسح الألغام؟",
             ["One nearby mine", "One life",
              "One player", "One flag"], 0),
        ],
    },

    "bank_manager": {
        "name": "Bank Manager",
        "name_ar": "مدير البنك",
        "emoji": "🏦",
        "questions": [
            ("You have 100 coins and spend 30. How much remains?",
             "لديك 100 عملة وأنفقت 30. كم يتبقى؟",
             ["60", "70", "80", "90"], 1),
        ],
    },

    "coin_flip": {
        "name": "Coin Flip",
        "name_ar": "رمي العملة",
        "emoji": "🪙",
        "questions": [
            ("Pick the winning side!",
             "اختر الوجه الفائز!",
             ["Heads", "Tails", "Both", "Neither"], 0),
        ],
    },

    "slots": {
        "name": "Slots",
        "name_ar": "آلة الحظ",
        "emoji": "🎰",
        "questions": [
            ("Which combination is the jackpot?",
             "أي تشكيلة تمثل الجائزة الكبرى؟",
             ["🍒🍋🍇", "⭐⭐⭐", "🍋🍒🍋", "🍇🍋🍒"], 1),
        ],
    },

    "safe_trap": {
        "name": "Safe or Trap",
        "name_ar": "آمن أم فخ",
        "emoji": "⚠️",
        "questions": [
            ("Choose the safest option!",
             "اختر الخيار الأكثر أمانًا!",
             ["Unknown link", "Verified source",
              "Suspicious file", "Unknown download"], 1),
        ],
    },
}


# ========================================================
# HELPERS
# ========================================================

def get_language(guild_id, user_id):

    try:
        player = get_player(guild_id, user_id)

        if player and player["active_language"] in ("ar", "en"):
            return player["active_language"]

    except Exception:
        logger.exception("Could not read player language")

    return "en"


def get_game(game_id):
    return GAMES.get(game_id)


def get_category_for_game(game_id):

    for category_id, category in CATEGORIES.items():
        if game_id in category["games"]:
            return category_id

    return None


def build_embed(title, description, color=PURPLE):

    return discord.Embed(
        title=title,
        description=description,
        color=color
    ).set_footer(
        text="MHN ARCADE V2.0 • Play • Compete • Win"
    )


def get_random_challenge(game_id):

    game = get_game(game_id)

    if not game:
        return None

    question = random.choice(game["questions"])

    prompt_en, prompt_ar, options, answer_index = question

    shuffled = list(enumerate(options))
    random.shuffle(shuffled)

    displayed_options = [
        {
            "label": option,
            "correct": original_index == answer_index
        }
        for original_index, option in shuffled
    ]

    return {
        "prompt_en": prompt_en,
        "prompt_ar": prompt_ar,
        "options": displayed_options,
    }


# ========================================================
# COOLDOWN
# ========================================================

class GameCooldown:

    def __init__(self):
        self.users = {}

    def remaining(self, user_id):

        last_used = self.users.get(user_id, 0)
        elapsed = time.monotonic() - last_used

        return max(0, COOLDOWN_SECONDS - elapsed)

    def update(self, user_id):
        self.users[user_id] = time.monotonic()


# ========================================================
# ANSWER BUTTON
# ========================================================

class AnswerButton(discord.ui.Button):

    def __init__(self, index, option, parent_view):

        self.parent_view = parent_view
        self.is_correct = option["correct"]

        super().__init__(
            label=option["label"][:80],
            style=discord.ButtonStyle.secondary,
            custom_id=f"mhn_arcade_answer_{index}",
            row=index // 2
        )

    async def callback(self, interaction: discord.Interaction):

        view = self.parent_view

        if interaction.user.id != view.player_id:
            await interaction.response.send_message(
                "هذه الجولة ليست لك! / This round belongs to another player.",
                ephemeral=True
            )
            return

        if view.finished:
            await interaction.response.send_message(
                "انتهت هذه الجولة بالفعل! / This round has ended.",
                ephemeral=True
            )
            return

        view.finished = True

        for item in view.children:
            item.disabled = True

        game = get_game(view.game_id)

        if self.is_correct:

            result = "win"
            xp_reward = 25
            coin_reward = 15

            title = "🏆 Correct Answer!"
            description = (
                f"أحسنت! إجابة صحيحة.\n"
                f"You earned **{xp_reward} XP** "
                f"and **{coin_reward} coins**."
            )

            color = 0x22C55E

        else:

            result = "loss"
            xp_reward = 8
            coin_reward = 0

            correct_option = next(
                option["label"]
                for option in view.challenge["options"]
                if option["correct"]
            )

            title = "❌ Incorrect Answer"
            description = (
                f"الإجابة الصحيحة: **{correct_option}**\n"
                f"Correct answer: **{correct_option}**\n\n"
                f"You earned **{xp_reward} XP** for participating."
            )

            color = 0xEF4444

        try:

            language = view.language

            record_game_result(
                guild_id=view.guild_id,
                user_id=view.player_id,
                username=interaction.user.display_name,
                language=language,
                game_id=view.game_id,
                result=result,
                xp_reward=xp_reward,
                coin_reward=coin_reward,
                score=1 if result == "win" else 0
            )

            result_embed = build_embed(
                title,
                description,
                color
            )

            result_embed.add_field(
                name="🎮 Game",
                value=game["name"],
                inline=True
            )

            result_embed.add_field(
                name="👤 Player",
                value=interaction.user.mention,
                inline=True
            )

            await interaction.response.edit_message(
                embed=result_embed,
                view=view
            )

        except Exception:

            logger.exception("Failed to save game result")

            await interaction.response.edit_message(
                embed=build_embed(
                    "⚠️ Game Result",
                    "تم إنهاء الجولة، لكن تعذر حفظ النتيجة. "
                    "يرجى إبلاغ الإدارة.",
                    0xEF4444
                ),
                view=view
            )


# ========================================================
# CHALLENGE VIEW
# ========================================================

class ChallengeView(discord.ui.View):

    def __init__(
        self,
        player_id,
        guild_id,
        game_id,
        language,
        challenge
    ):

        super().__init__(timeout=90)

        self.player_id = player_id
        self.guild_id = guild_id
        self.game_id = game_id
        self.language = language
        self.challenge = challenge
        self.finished = False

        for index, option in enumerate(challenge["options"]):
            self.add_item(
                AnswerButton(index, option, self)
            )

    async def interaction_check(self, interaction):

        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "هذه اللعبة مخصصة للاعب الذي بدأها.",
                ephemeral=True
            )
            return False

        return True

    async def on_timeout(self):

        if self.finished:
            return

        self.finished = True

        for item in self.children:
            item.disabled = True

        try:
            if self.message:
                await self.message.edit(
                    embed=build_embed(
                        "⏰ Time's Up!",
                        "انتهى الوقت! لم يتم تسجيل نتيجة لهذه الجولة.",
                        0xEF4444
                    ),
                    view=self
                )
        except (discord.NotFound, discord.HTTPException):
            pass


# ========================================================
# GAME PICKER
# ========================================================

class GamePicker(discord.ui.Select):

    def __init__(self, category_id, player_id, guild_id, language):

        self.category_id = category_id
        self.player_id = player_id
        self.guild_id = guild_id
        self.language = language

        category = CATEGORIES[category_id]

        options = []

        for game_id in category["games"]:

            game = GAMES[game_id]

            label = (
                game["name_ar"]
                if language == "ar"
                else game["name"]
            )

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=game_id,
                    emoji=game["emoji"]
                )
            )

        super().__init__(
            placeholder=(
                "اختر لعبة للبدء"
                if language == "ar"
                else "Choose a game to play"
            ),
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"mhn_arcade_picker_{category_id}"
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "هذه القائمة ليست لك.",
                ephemeral=True
            )
            return

        game_id = self.values[0]
        game = get_game(game_id)

        challenge = get_random_challenge(game_id)

        if not challenge:
            await interaction.response.send_message(
                "تعذر تحميل اللعبة.",
                ephemeral=True
            )
            return

        prompt = (
            challenge["prompt_ar"]
            if self.language == "ar"
            else challenge["prompt_en"]
        )

        description = (
            f"**{prompt}**\n\n"
            "اختر إجابتك من الأزرار بالأسفل."
            if self.language == "ar"
            else f"**{prompt}**\n\nChoose your answer below."
        )

        embed = build_embed(
            f"{game['emoji']} {game['name']}",
            description
        )

        embed.add_field(
            name="👤 Player",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="⏱️ Time",
            value="90 seconds",
            inline=True
        )

        view = ChallengeView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            game_id=game_id,
            language=self.language,
            challenge=challenge
        )

        await interaction.response.edit_message(
            embed=embed,
            view=view
        )

        view.message = await interaction.original_response()


class GamePickerView(discord.ui.View):

    def __init__(self, category_id, player_id, guild_id, language):

        super().__init__(timeout=120)

        self.add_item(
            GamePicker(
                category_id,
                player_id,
                guild_id,
                language
            )
        )


# ========================================================
# CATEGORY BUTTON
# ========================================================

class CategoryButton(discord.ui.Button):

    def __init__(self, category_id, player_id, guild_id, language):

        self.category_id = category_id
        self.player_id = player_id
        self.guild_id = guild_id
        self.language = language

        category = CATEGORIES[category_id]

        label = (
            category["name_ar"]
            if language == "ar"
            else category["name"]
        )

        super().__init__(
            label=label,
            emoji=category["emoji"],
            style=discord.ButtonStyle.primary,
            custom_id=f"mhn_arcade_category_{category_id}"
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "هذه القائمة ليست لك.",
                ephemeral=True
            )
            return

        category = CATEGORIES[self.category_id]

        category_name = (
            category["name_ar"]
            if self.language == "ar"
            else category["name"]
        )

        description = (
            f"اختر لعبة من فئة **{category_name}**."
            if self.language == "ar"
            else f"Choose a game from **{category_name}**."
        )

        view = GamePickerView(
            self.category_id,
            self.player_id,
            self.guild_id,
            self.language
        )

        await interaction.response.edit_message(
            embed=build_embed(
                f"{category['emoji']} {category_name}",
                description
            ),
            view=view
        )


# ========================================================
# ARCADE HOME VIEW
# ========================================================

class ArcadeHomeView(discord.ui.View):

    def __init__(self, player_id, guild_id, language):

        super().__init__(timeout=180)

        self.player_id = player_id
        self.guild_id = guild_id
        self.language = language

        for category_id in CATEGORIES:

            self.add_item(
                CategoryButton(
                    category_id,
                    player_id,
                    guild_id,
                    language
                )
            )

    async def interaction_check(self, interaction):

        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "افتح قائمة الألعاب الخاصة بك باستخدام /arcade.",
                ephemeral=True
            )
            return False

        return True


# ========================================================
# ARCADE COG
# ========================================================

class ArcadeGames(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.cooldown = GameCooldown()

    @app_commands.command(
        name="arcade",
        description="Open the MHN ARCADE V2.0 games menu."
    )
    @app_commands.guild_only()
    async def arcade(self, interaction: discord.Interaction):

        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True
            )
            return

        remaining = self.cooldown.remaining(interaction.user.id)

        if remaining > 0:

            await interaction.response.send_message(
                f"انتظر {remaining:.1f} ثانية قبل فتح القائمة مرة أخرى.",
                ephemeral=True
            )
            return

        self.cooldown.update(interaction.user.id)

        guild_id = interaction.guild.id
        player_id = interaction.user.id

        language = get_language(guild_id, player_id)

        view = ArcadeHomeView(
            player_id,
            guild_id,
            language
        )

        if language == "ar":

            embed = build_embed(
                "💜 MHN ARCADE V2.0",
                (
                    "أهلًا بك في صالة الألعاب!\n\n"
                    "**اختر نوع الألعاب:**\n"
                    "🏆 المنافسة والتحديات\n"
                    "⚡ السرعة وردة الفعل\n"
                    "🧠 الذكاء والألغاز\n"
                    "🎲 الحظ والاستراتيجية\n\n"
                    "اختر فئة للبدء."
                )
            )

        else:

            embed = build_embed(
                "💜 MHN ARCADE V2.0",
                (
                    "Welcome to the arcade!\n\n"
                    "**Choose your game category:**\n"
                    "🏆 Social & Competition\n"
                    "⚡ Speed & Reflex\n"
                    "🧠 Brain & Puzzle\n"
                    "🎲 Luck & Strategy\n\n"
                    "Select a category to begin."
                )
            )

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

    @app_commands.command(
        name="arcade_stats",
        description="View your arcade game statistics."
    )
    @app_commands.guild_only()
    async def arcade_stats(self, interaction: discord.Interaction):

        guild_id = interaction.guild.id
        player_id = interaction.user.id

        language = get_language(guild_id, player_id)

        # Read individual game statistics from the database.
        from database import get_game_stats

        try:

            stats = get_game_stats(
                guild_id,
                player_id
            )

            if not stats:

                message = (
                    "لم تلعب أي لعبة حتى الآن."
                    if language == "ar"
                    else "You haven't played any games yet."
                )

                await interaction.response.send_message(
                    message,
                    ephemeral=True
                )
                return

            total_games = sum(row["games_played"] for row in stats)
            total_wins = sum(row["wins"] for row in stats)
            total_losses = sum(row["losses"] for row in stats)

            lines = []

            for row in stats[:10]:

                game = GAMES.get(row["game_id"])

                if game:
                    game_name = (
                        game["name_ar"]
                        if language == "ar"
                        else game["name"]
                    )
                else:
                    game_name = row["game_id"]

                lines.append(
                    f"{game['emoji'] if game else '🎮'} "
                    f"**{game_name}** — "
                    f"{row['games_played']} games | "
                    f"{row['wins']} wins"
                )

            description = "\n".join(lines)

            embed = build_embed(
                "📊 إحصائيات الألعاب"
                if language == "ar"
                else "📊 Arcade Statistics",
                description
            )

            embed.add_field(
                name="🎮 Games",
                value=str(total_games),
                inline=True
            )

            embed.add_field(
                name="🏆 Wins",
                value=str(total_wins),
                inline=True
            )

            embed.add_field(
                name="❌ Losses",
                value=str(total_losses),
                inline=True
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except Exception:

            logger.exception("Could not load arcade statistics")

            await interaction.response.send_message(
                "تعذر تحميل الإحصائيات حاليًا.",
                ephemeral=True
            )


# ========================================================
# SETUP
# ========================================================

async def setup(bot):

    await bot.add_cog(ArcadeGames(bot))

    logger.info("MHN ARCADE V2.0 Games Engine loaded.")
