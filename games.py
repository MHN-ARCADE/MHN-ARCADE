"""MHN ARCADE V2.0 — interactive single-player arcade engine.
Requires discord.py 2.7.1 and database.record_game_result/get_player/get_game_stats.
All games are playable solo challenges against the game engine. Multiplayer rooms
are intentionally not advertised until their lobby/turn system is implemented.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from database import record_game_result, get_player, get_game_stats

log = logging.getLogger("mhn.arcade.games")
PURPLE = 0x7C3AED
GREEN = 0x22C55E
RED = 0xEF4444
GOLD = 0xF59E0B
COOLDOWN_SECONDS = 8
SESSION_TIMEOUT = 120

CATEGORIES: dict[str, dict[str, Any]] = {
    "social": {"name": "Social & Competition", "name_ar": "المنافسة والتحديات", "emoji": "🏆", "games": ["musical_chairs", "roulette", "mafia", "impostor", "hide_seek", "dice_battle", "rps", "guess_who"]},
    "speed": {"name": "Speed & Reflex", "name_ar": "السرعة وردة الفعل", "emoji": "⚡", "games": ["fast_click", "fast_type", "text_split", "unscramble", "find_emoji", "color_match", "sort_numbers"]},
    "brain": {"name": "Brain & Puzzle", "name_ar": "الذكاء والألغاز", "emoji": "🧠", "games": ["memory", "trivia", "riddles", "guess_character", "guess_anime", "guess_flag", "hangman", "wordle"]},
    "luck": {"name": "Luck & Strategy", "name_ar": "الحظ والاستراتيجية", "emoji": "🎲", "games": ["tic_tac_toe", "connect_four", "minesweeper", "bank_manager", "coin_flip", "slots", "safe_trap"]},
}

# Display names and short descriptions are deliberately separate from mechanics.
GAMES: dict[str, dict[str, str]] = {
    "musical_chairs": {"name":"Musical Chairs","name_ar":"الكراسي الموسيقية","emoji":"🪑"},
    "roulette": {"name":"Elimination Roulette","name_ar":"روليت الإقصاء","emoji":"🎯"},
    "mafia": {"name":"Mafia Detective","name_ar":"محقق المافيا","emoji":"🕵️"},
    "impostor": {"name":"Impostor","name_ar":"المحتال","emoji":"🎭"},
    "hide_seek": {"name":"Hide & Seek","name_ar":"الغميضة","emoji":"🙈"},
    "dice_battle": {"name":"Dice Battle","name_ar":"معركة النرد","emoji":"🎲"},
    "rps": {"name":"Rock Paper Scissors","name_ar":"حجر ورقة مقص","emoji":"✊"},
    "guess_who": {"name":"Guess Who","name_ar":"من أنا؟","emoji":"❓"},
    "fast_click": {"name":"Fast Click","name_ar":"النقرة السريعة","emoji":"⚡"},
    "fast_type": {"name":"Fast Type","name_ar":"الكتابة السريعة","emoji":"⌨️"},
    "text_split": {"name":"Text Split","name_ar":"ترتيب الكلمات","emoji":"🔤"},
    "unscramble": {"name":"Unscramble","name_ar":"فك الحروف","emoji":"🔠"},
    "find_emoji": {"name":"Find Emoji","name_ar":"اكتشف الإيموجي","emoji":"🔎"},
    "color_match": {"name":"Color Match","name_ar":"مطابقة الألوان","emoji":"🎨"},
    "sort_numbers": {"name":"Sort Numbers","name_ar":"ترتيب الأرقام","emoji":"🔢"},
    "memory": {"name":"Memory Sequence","name_ar":"تحدي الذاكرة","emoji":"🧩"},
    "trivia": {"name":"Trivia","name_ar":"معلومات عامة","emoji":"📚"},
    "riddles": {"name":"Riddles","name_ar":"الألغاز","emoji":"💡"},
    "guess_character": {"name":"Guess the Character","name_ar":"خمن الشخصية","emoji":"🎬"},
    "guess_anime": {"name":"Guess the Anime","name_ar":"خمن الأنمي","emoji":"⛩️"},
    "guess_flag": {"name":"Guess the Flag","name_ar":"خمن العلم","emoji":"🌍"},
    "hangman": {"name":"Hangman","name_ar":"الرجل المشنوق","emoji":"🔡"},
    "wordle": {"name":"Wordle","name_ar":"ووردل","emoji":"🟩"},
    "tic_tac_toe": {"name":"Tic Tac Toe","name_ar":"إكس أو","emoji":"⭕"},
    "connect_four": {"name":"Connect Four","name_ar":"أربع على التوالي","emoji":"🔴"},
    "minesweeper": {"name":"Minesweeper","name_ar":"كاسح الألغام","emoji":"💣"},
    "bank_manager": {"name":"Bank Manager","name_ar":"مدير البنك","emoji":"🏦"},
    "coin_flip": {"name":"Coin Flip","name_ar":"رمي العملة","emoji":"🪙"},
    "slots": {"name":"Slots","name_ar":"آلة الحظ","emoji":"🎰"},
    "safe_trap": {"name":"Safe or Trap","name_ar":"آمن أم فخ","emoji":"⚠️"},
}

# Content pools: every play selects a fresh question/answer or randomized board.
QUIZZES = {
 "trivia": [
  ("What is the largest planet?","ما أكبر كوكب؟",["Earth","Mars","Jupiter","Venus"],2),
  ("How many sides does a hexagon have?","كم ضلعًا للشكل السداسي؟",["5","6","7","8"],1),
  ("Which ocean is the largest?","ما أكبر محيط؟",["Atlantic","Indian","Arctic","Pacific"],3),
  ("What is the chemical symbol for gold?","ما رمز الذهب الكيميائي؟",["Ag","Au","Fe","Go"],1),
 ],
 "riddles": [
  ("What has keys but cannot open locks?","ما له مفاتيح ولا يفتح الأقفال؟",["A piano","A map","A clock","A book"],0),
  ("What gets wetter as it dries?","ما الشيء الذي يزداد بللًا كلما جفف؟",["A towel","A sponge","Rain","Ice"],0),
  ("What has a face and two hands but no arms?","له وجه وعقربان وليس له ذراعان؟",["A clock","A doll","A robot","A mirror"],0),
 ],
 "guess_character": [
  ("I am the King of Curses.","أنا ملك اللعنات.",["Gojo","Sukuna","Levi","Ichigo"],1),
  ("I use the Six Eyes and Limitless.","أمتلك العيون الست وتقنية اللامحدود.",["Toji","Aizen","Gojo","Urahara"],2),
  ("I am a captain who planned far ahead in Soul Society.","قائد خطط لكل شيء في مجتمع الأرواح.",["Ichigo","Aizen","Levi","Goku"],1),
  ("I am humanity's strongest soldier.","أنا أقوى جندي للبشرية.",["Levi","Toji","Sukuna","Urahara"],0),
 ],
 "guess_anime": [
  ("Which anime features Levi Ackerman?","في أي أنمي تظهر شخصية ليفاي؟",["Naruto","Bleach","Attack on Titan","One Piece"],2),
  ("Which anime features the Soul Society?","أي أنمي يظهر فيه مجتمع الأرواح؟",["Bleach","Jujutsu Kaisen","Dragon Ball","Demon Slayer"],0),
  ("Which anime features the Hidden Leaf Village?","أي أنمي تظهر فيه قرية الورق المخفية؟",["One Piece","Naruto","Bleach","Death Note"],1),
 ],
 "guess_flag": [
  ("🇯🇵","Which country is this?","ما الدولة التي يمثلها هذا العلم؟",["Japan","China","South Korea","Thailand"],0),
  ("🇧🇷","Which country is this?","ما الدولة التي يمثلها هذا العلم؟",["Portugal","Brazil","Mexico","Argentina"],1),
  ("🇨🇦","Which country is this?","ما الدولة التي يمثلها هذا العلم؟",["USA","Denmark","Canada","Austria"],2),
  ("🇸🇦","Which country is this?","ما الدولة التي يمثلها هذا العلم؟",["Saudi Arabia","Pakistan","Algeria","Morocco"],0),
 ],
}

WORDS = ["ARCADE", "GAMER", "PIXEL", "QUEST", "LEVEL", "NINJA", "SWORD", "ROBOT"]
HANGMAN_WORDS = ["PYTHON", "GAMING", "ARCADE", "PLAYER", "NINJA"]
WORDLE_WORDS = ["LEVEL", "GAMES", "PIXEL", "QUEST", "NINJA", "SWORD"]
COLORS = [("RED","🔴"),("BLUE","🔵"),("GREEN","🟢"),("YELLOW","🟡")]


def get_language(guild_id: int, user_id: int) -> str:
    try:
        player = get_player(guild_id, user_id)
        if player:
            lang = player["active_language"]
            if lang in ("ar", "en"):
                return lang
    except Exception:
        log.exception("Could not read player language")
    return "en"


def build_embed(title: str, description: str, color: int = PURPLE) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.set_footer(text="MHN ARCADE V2.0 • Play • Compete • Win")
    return e


def game_label(game_id: str, lang: str) -> str:
    g = GAMES[game_id]
    return g["name_ar"] if lang == "ar" else g["name"]


class GameCooldown:
    def __init__(self): self.users: dict[int, float] = {}
    def remaining(self, user_id: int) -> float:
        return max(0.0, COOLDOWN_SECONDS - (time.monotonic() - self.users.get(user_id, 0.0)))
    def update(self, user_id: int): self.users[user_id] = time.monotonic()


class ActionButton(discord.ui.Button):
    def __init__(self, view: "GameSessionView", label: str, action: str, *, emoji: str | None = None, style=discord.ButtonStyle.secondary, row: int | None = None):
        self.session = view
        self.action = action
        super().__init__(label=label[:80], emoji=emoji, style=style, row=row)
    async def callback(self, interaction: discord.Interaction):
        await self.session.handle_action(interaction, self.action)


class GameSelect(discord.ui.Select):
    def __init__(self, category_id: str, owner_id: int, guild_id: int, lang: str):
        self.category_id, self.owner_id, self.guild_id, self.lang = category_id, owner_id, guild_id, lang
        cat = CATEGORIES[category_id]
        opts = [discord.SelectOption(label=game_label(gid, lang)[:100], value=gid, emoji=GAMES[gid]["emoji"]) for gid in cat["games"]]
        super().__init__(placeholder="اختر لعبة" if lang == "ar" else "Choose a game", min_values=1, max_values=1, options=opts)
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("هذه القائمة ليست لك. / This menu isn't yours.", ephemeral=True)
        view = GameSessionView(self.owner_id, self.guild_id, self.values[0], self.lang)
        await view.start(interaction)


class GameSelectView(discord.ui.View):
    def __init__(self, category_id: str, owner_id: int, guild_id: int, lang: str):
        super().__init__(timeout=150)
        self.add_item(GameSelect(category_id, owner_id, guild_id, lang))


class CategoryButton(discord.ui.Button):
    def __init__(self, category_id: str, owner_id: int, guild_id: int, lang: str):
        self.category_id, self.owner_id, self.guild_id, self.lang = category_id, owner_id, guild_id, lang
        cat = CATEGORIES[category_id]
        super().__init__(label=(cat["name_ar"] if lang == "ar" else cat["name"]), emoji=cat["emoji"], style=discord.ButtonStyle.primary, row=list(CATEGORIES).index(category_id))
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("افتح قائمتك باستخدام /arcade. / Open your own /arcade menu.", ephemeral=True)
        cat = CATEGORIES[self.category_id]
        name = cat["name_ar"] if self.lang == "ar" else cat["name"]
        desc = f"اختر لعبة من **{name}**." if self.lang == "ar" else f"Choose a game from **{name}**."
        await interaction.response.edit_message(embed=build_embed(f"{cat['emoji']} {name}", desc), view=GameSelectView(self.category_id, self.owner_id, self.guild_id, self.lang))


class ArcadeHomeView(discord.ui.View):
    def __init__(self, owner_id: int, guild_id: int, lang: str):
        super().__init__(timeout=180)
        for cid in CATEGORIES:
            self.add_item(CategoryButton(cid, owner_id, guild_id, lang))
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.children:
            return False
        owner = self.children[0].owner_id
        if interaction.user.id != owner:
            await interaction.response.send_message("هذه القائمة ليست لك. / This menu isn't yours.", ephemeral=True)
            return False
        return True


class TextEntryModal(discord.ui.Modal):
    def __init__(self, session: "GameSessionView", title: str, label: str, placeholder: str = ""):
        super().__init__(title=title[:45], timeout=60)
        self.session = session
        self.answer = discord.ui.TextInput(label=label[:45], placeholder=placeholder[:100] or None, max_length=80, required=True)
        self.add_item(self.answer)
    async def on_submit(self, interaction: discord.Interaction):
        await self.session.handle_text(interaction, str(self.answer.value))


class GameSessionView(discord.ui.View):
    """Shared interaction shell; each game has its own state machine."""
    def __init__(self, player_id: int, guild_id: int, game_id: str, lang: str):
        super().__init__(timeout=20 if game_id == "fast_click" else SESSION_TIMEOUT)
        self.player_id, self.guild_id, self.game_id, self.lang = player_id, guild_id, game_id, lang
        self.state: dict[str, Any] = {}
        self.finished = False
        self.message: discord.Message | None = None
        self.started = time.monotonic()
        self.result_text = ""
        self._build_game()

    @property
    def ar(self) -> bool: return self.lang == "ar"
    def tr(self, en: str, ar: str) -> str: return ar if self.ar else en
    def title(self) -> str: return f"{GAMES[self.game_id]['emoji']} {game_label(self.game_id, self.lang)}"
    def add_action(self, label: str, action: str, emoji: str | None = None, style=discord.ButtonStyle.secondary, row: int | None = None):
        self.add_item(ActionButton(self, label, action, emoji=emoji, style=style, row=row))
    def clear_actions(self): self.clear_items()
    def set_prompt(self, prompt: str, color: int = PURPLE): self.embed = build_embed(self.title(), prompt, color)
    async def start(self, interaction: discord.Interaction):
        self._render()
        await interaction.response.edit_message(embed=self.embed, view=self)
        try: self.message = await interaction.original_response()
        except discord.HTTPException: self.message = None

    def _build_game(self):
        g = self.game_id
        if g == "musical_chairs":
            self.state.update(round=1, lives=3, chairs=4)
            self._chairs()
        elif g == "roulette":
            self.state.update(round=1, rounds=5, lives=3)
            self._roulette()
        elif g == "mafia":
            cases = [
                ("The vault was robbed. The door opens only with the banker's unique key, and the lock shows no damage. Who is the strongest suspect?", "سُرقت الخزنة. لا يفتح بابها إلا مفتاح المصرفي الخاص، ولا توجد آثار كسر. من المشتبه به الأقوى؟", ["The guard / الحارس", "The banker / المصرفي", "The chef / الطاهي", "The gardener / البستاني"], 1),
                ("The museum alarm was disabled with a staff code. Only the curator knew that code, and the code was used at the exact time of the theft. Who is the strongest suspect?", "عُطّل إنذار المتحف برمز للموظفين. أمين المتحف وحده يعرف الرمز، واستُخدم وقت السرقة. من المشتبه به الأقوى؟", ["The visitor / الزائر", "The cleaner / عامل النظافة", "The curator / أمين المتحف", "The driver / السائق"], 2),
            ]
            self.state["quiz"] = random.choice(cases); self._quiz_prompt("case")
        elif g == "impostor":
            groups = [
                (("Apple","Banana","Car","Orange"), "Car"),
                (("Mercury","Venus","Mars","Pizza"), "Pizza"),
                (("Sword","Shield","Helmet","Banana"), "Banana"),
                (("Piano","Guitar","Drums","Mountain"), "Mountain"),
            ]
            group, odd_item = random.choice(groups)
            self.state["options"] = list(group)
            self.state["correct"] = odd_item
            random.shuffle(self.state["options"])
            self._choice_prompt(self.tr("Find the impostor item.","اكتشف العنصر الدخيل."), self.state["options"])
        elif g == "hide_seek":
            spots = ["Closet / الخزانة","Behind sofa / خلف الأريكة","Under table / تحت الطاولة","Garden shed / مخزن الحديقة"]
            clues = {
                spots[0]: ("I am hiding where coats and jackets hang.", "أختبئ في المكان الذي تُعلّق فيه المعاطف والسترات."),
                spots[1]: ("I am behind the furniture you sit on to relax.", "أختبئ خلف الأثاث الذي تجلس عليه للاسترخاء."),
                spots[2]: ("I am beneath the place where people eat together.", "أختبئ تحت المكان الذي يجتمع الناس حوله لتناول الطعام."),
                spots[3]: ("I am inside the small place where garden tools are kept.", "أختبئ في المكان الصغير الذي تُحفظ فيه أدوات الحديقة."),
            }
            self.state["correct"] = random.choice(spots)
            self.state["options"] = spots
            clue = clues[self.state["correct"]][1 if self.ar else 0]
            self._choice_prompt(self.tr(f"Find the hidden player. Clue: {clue}", f"اعثر على اللاعب المختبئ. التلميح: {clue}"), spots)
        elif g == "dice_battle": self.state.update(round=1, you=0, bot=0); self._dice()
        elif g == "rps": self.state.update(round=1, you=0, bot=0); self._rps()
        elif g == "guess_who":
            self.state["quiz"] = ("I have four legs, bark, and wag my tail.","لدي أربع أرجل وأنبح وأهز ذيلي.",["Cat / قطة","Dog / كلب","Horse / حصان","Wolf / ذئب"],1); self._quiz_prompt("quiz")
        elif g == "fast_click": self.state.update(count=0, target=7); self._fast_click()
        elif g in ("fast_type", "text_split", "unscramble"):
            word = random.choice(WORDS)
            if g == "fast_type": self.state["answer"] = word; self.state["display"] = word
            elif g == "text_split":
                phrase = random.choice(["PLAY THE GAME","LEVEL UP NOW","JOIN THE ARCADE"]); self.state["answer"] = phrase; self.state["display"] = " / ".join(phrase.split())
            else:
                self.state["answer"] = word; chars = list(word); random.shuffle(chars)
                while "".join(chars) == word: random.shuffle(chars)
                self.state["display"] = " ".join(chars)
            self._text_prompt()
        elif g == "find_emoji":
            target = random.choice(["🎮","🎯","🎧","🕹️"]); pool = ["🎲","🎨","⚽","🎵","🎁","🎤","🎮","🎯","🎧","🕹️"]; pool = random.sample(pool, 9); pool[random.randrange(9)] = target; self.state.update(target=target, pool=pool); self._emoji_grid()
        elif g == "color_match":
            target, _ = random.choice(COLORS); opts = random.sample(COLORS, 4); self.state.update(target=target, options=opts); self._color()
        elif g == "sort_numbers":
            nums = random.sample(range(1, 50), 5); self.state.update(nums=nums, sorted=sorted(nums), index=0); self._sort()
        elif g == "memory":
            seq = [random.choice(["🔴","🔵","🟢","🟡"]) for _ in range(5)]; self.state.update(seq=seq, answer="".join(seq), stage="memorize"); self._memory()
        elif g in QUIZZES:
            self.state["quiz"] = random.choice(QUIZZES[g]); self._quiz_prompt("quiz")
        elif g == "hangman": self.state.update(word=random.choice(HANGMAN_WORDS), guessed=set(), misses=0); self._hangman()
        elif g == "wordle": self.state.update(word=random.choice(WORDLE_WORDS), tries=0, guesses=[]); self._wordle()
        elif g == "tic_tac_toe": self.state.update(board=[" "]*9, turn="X"); self._ttt()
        elif g == "connect_four": self.state.update(board=[[" "]*7 for _ in range(6)], turn="R"); self._connect()
        elif g == "minesweeper": self.state.update(mines=set(random.sample(range(16), 3)), revealed=set(), safe_needed=7); self._mines()
        elif g == "bank_manager": self.state.update(cash=100, round=1); self._bank()
        elif g == "coin_flip": self.state.update(choice=None); self._coin()
        elif g == "slots": self.state.update(spins=3, symbols=["🍒","🍋","🍇","⭐","🔔"]); self._slots()
        elif g == "safe_trap": self.state.update(round=1, lives=2, safe=random.sample(range(1,6), 3)); self._safe_trap()

    def _choice_prompt(self, prompt: str, options: list[str]):
        self.clear_actions(); self.set_prompt(prompt)
        for i, option in enumerate(options): self.add_action(option, f"choice:{i}", row=i//2)
        self._render()

    def _quiz_prompt(self, kind: str):
        q = self.state["quiz"]
        if self.game_id == "guess_flag":
            flag, prompt_en, prompt_ar, opts, answer_index = q
            prompt = f"{flag}\n{prompt_ar if self.ar else prompt_en}"
        else:
            prompt = q[0] if not self.ar else q[1]
            opts, answer_index = q[2], q[3]
        self.state["options"] = opts
        self.state["answer_index"] = answer_index
        self._choice_prompt(prompt, opts)

    def _chairs(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Round {self.state['round']}/5 • {self.state['lives']} lives left. Pick a chair before the music stops!", f"الجولة {self.state['round']}/5 • بقيت {self.state['lives']} محاولات. اختر كرسيًا قبل توقف الموسيقى!"))
        for n in range(1,5): self.add_action(f"Chair {n}" if not self.ar else f"كرسي {n}", f"chair:{n}", emoji="🪑", row=(n-1)//2)
        self._render()
    def _roulette(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Round {self.state['round']}/5. Pick one of five chambers. You have {self.state['lives']} lives.", f"الجولة {self.state['round']}/5. اختر خانة من خمس. لديك {self.state['lives']} محاولات."))
        for n in range(1,6): self.add_action(str(n), f"roulette:{n}", row=(n-1)//3)
        self._render()
    def _dice(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Best of 3 rounds. Score — You: {self.state['you']} | Arcade: {self.state['bot']}", f"أفضل من 3 جولات. النتيجة — أنت: {self.state['you']} | الآركيد: {self.state['bot']}"))
        self.add_action(self.tr("Roll dice","ارمِ النرد"), "dice", "🎲", discord.ButtonStyle.primary); self._render()
    def _rps(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Best of 3 • You {self.state['you']} — {self.state['bot']} Arcade", f"أفضل من 3 • أنت {self.state['you']} — {self.state['bot']} الآركيد"))
        for label, val, em in [("Rock","rock","✊"),("Paper","paper","✋"),("Scissors","scissors","✌️")]: self.add_action(label if not self.ar else {"rock":"حجر","paper":"ورقة","scissors":"مقص"}[val], f"rps:{val}", em, row=0)
        self._render()
    def _fast_click(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Tap the target {self.state['target']} times. Progress: {self.state['count']}/{self.state['target']}", f"اضغط الهدف {self.state['target']} مرات. التقدم: {self.state['count']}/{self.state['target']}"))
        self.add_action(self.tr("CLICK!","اضغط!"), "click", "⚡", discord.ButtonStyle.success); self._render()
    def _text_prompt(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Type this exactly: **{self.state['display']}**", f"اكتب النص كما هو تمامًا: **{self.state['display']}**"))
        self.add_action(self.tr("Enter answer","إدخال الإجابة"), "modal", "⌨️", discord.ButtonStyle.primary); self._render()
    def _emoji_grid(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Find {self.state['target']} in the grid!", f"اعثر على {self.state['target']} في الشبكة!"))
        for i, em in enumerate(self.state["pool"]): self.add_action(em, f"emoji:{i}", row=i//3)
        self._render()
    def _color(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Tap the color {self.state['target']}.", f"اضغط اللون {self.state['target']}"))
        for i, (name, em) in enumerate(self.state["options"]): self.add_action(name.title(), f"color:{name}", em, row=i//2)
        self._render()
    def _sort(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Tap the numbers from smallest to largest. Next: {self.state['sorted'][self.state['index']]} • {self.state['index']}/5", f"اضغط الأرقام من الأصغر للأكبر. التالي: {self.state['sorted'][self.state['index']]} • {self.state['index']}/5"))
        for i, n in enumerate(self.state["nums"]): self.add_action(str(n), f"sort:{n}", row=i//3)
        self._render()
    def _memory(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Memorize this sequence, then press Ready: **{' '.join(self.state['seq'])}**", f"احفظ هذا التسلسل ثم اضغط جاهز: **{' '.join(self.state['seq'])}**"))
        self.add_action(self.tr("Ready","جاهز"), "memory_ready", "🧠", discord.ButtonStyle.primary); self._render()
    def _hangman(self):
        self.clear_actions(); word=self.state["word"]; guessed=self.state["guessed"]
        shown=" ".join(c if c in guessed else "＿" for c in word)
        self.set_prompt(self.tr(f"Guess the word: **{shown}**\nWrong guesses: {self.state['misses']}/6", f"خمن الكلمة: **{shown}**\nالأخطاء: {self.state['misses']}/6"))
        self.add_action(self.tr("Guess a letter","خمن حرفًا"), "hangman_modal", "🔤", discord.ButtonStyle.primary)
        self._render()
    def _wordle(self):
        self.clear_actions(); lines=[]
        for guess in self.state["guesses"]:
            marks=" ".join("🟩" if a==b else ("🟨" if a in self.state["word"] else "⬛") for a,b in zip(guess,self.state["word"]))
            lines.append(f"`{guess}`  {marks}")
        self.set_prompt(self.tr(f"Guess the 5-letter word • {self.state['tries']}/6 tries\n"+"\n".join(lines), f"خمن الكلمة من 5 أحرف • المحاولات {self.state['tries']}/6\n"+"\n".join(lines)))
        self.add_action(self.tr("Enter 5-letter guess","أدخل كلمة من 5 أحرف"), "wordle_modal", "⌨️", discord.ButtonStyle.primary); self._render()
    def _ttt(self):
        self.clear_actions(); board=self.state["board"]
        self.set_prompt(self.tr("You are X. Get three in a row before the Arcade bot.","أنت X. كوّن ثلاثة رموز متتالية قبل خصم الآركيد.")+"\n\n"+" | ".join(board[:3])+"\n---------\n"+" | ".join(board[3:6])+"\n---------\n"+" | ".join(board[6:]))
        for i,v in enumerate(board): self.add_action(v if v!=" " else str(i+1), f"ttt:{i}", row=i//3, style=discord.ButtonStyle.primary if v=="X" else discord.ButtonStyle.secondary)
        self._render()
    def _connect(self):
        board=self.state["board"]; rows=["".join("🔴" if c=="R" else ("🟡" if c=="Y" else "⚫") for c in row) for row in board]
        self.clear_actions(); self.set_prompt(self.tr("You are 🔴. Choose a column; connect four to win.\n","أنت 🔴. اختر عمودًا ووصل أربع قطع للفوز.\n")+"\n".join(rows))
        for c in range(7): self.add_action(str(c+1), f"connect:{c}", row=c//5)
        self._render()
    def _mines(self):
        self.clear_actions(); revealed=self.state["revealed"]; board=[]
        for i in range(16): board.append("💣" if i in revealed and i in self.state["mines"] else ("🟩" if i in revealed else "⬜"))
        self.set_prompt(self.tr(f"Reveal {self.state['safe_needed']} safe tiles. Safe found: {len(revealed)}/{self.state['safe_needed']}\n", f"اكشف {self.state['safe_needed']} مربعات آمنة. المكتشف: {len(revealed)}/{self.state['safe_needed']}\n")+" ".join(board))
        for i in range(16):
            if i not in revealed: self.add_action(str(i+1), f"mine:{i}", row=i//4)
        self._render()
    def _bank(self):
        self.clear_actions(); self.set_prompt(self.tr(f"You have {self.state['cash']} coins. Choose one investment. Two rounds remain after this one.", f"لديك {self.state['cash']} عملة. اختر استثمارًا. تبقى جولتان بعد هذه."))
        for label, act, em in [("Safe +10%","bank:safe","🛡️"),("Balanced +25% / -10%","bank:balanced","⚖️"),("Risky +60% / -35%","bank:risky","🔥")]: self.add_action(label if not self.ar else {"bank:safe":"آمن +10%","bank:balanced":"متوازن +25% / -10%","bank:risky":"مخاطرة +60% / -35%"}[act], act, em, row=0)
        self._render()
    def _coin(self):
        self.clear_actions(); self.set_prompt(self.tr("Predict the coin side.","توقع وجه العملة."))
        self.add_action(self.tr("Heads","صورة"), "coin:Heads", "🪙"); self.add_action(self.tr("Tails","كتابة"), "coin:Tails", "🪙")
        self._render()
    def _slots(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Spin the reels. Spins left: {self.state['spins']}\n{self.state.get('last','🎰 🎰 🎰')}", f"أدر البكرات. المحاولات المتبقية: {self.state['spins']}\n{self.state.get('last','🎰 🎰 🎰')}"))
        self.add_action(self.tr("SPIN","لفّ"), "spin", "🎰", discord.ButtonStyle.primary); self._render()
    def _safe_trap(self):
        self.clear_actions(); self.set_prompt(self.tr(f"Round {self.state['round']}/3 • {self.state['lives']} lives. Find a safe tile.", f"الجولة {self.state['round']}/3 • {self.state['lives']} محاولات. اعثر على المربع الآمن."))
        for n in range(1,6): self.add_action(f"Tile {n}" if not self.ar else f"مربع {n}", f"safe:{n}", row=(n-1)//3)
        self._render()
    def _render(self):
        if not hasattr(self,"embed"): self.embed=build_embed(self.title(), self.tr("Choose an action.","اختر حركة."))

    async def handle_action(self, interaction: discord.Interaction, action: str):
        if interaction.user.id != self.player_id:
            return await interaction.response.send_message("هذه الجولة ليست لك. / This round isn't yours.", ephemeral=True)
        if self.finished:
            return await interaction.response.send_message("انتهت الجولة. / This round has ended.", ephemeral=True)
        g=self.game_id; s=self.state
        if action in ("modal","wordle_modal","hangman_modal"):
            title = (self.tr("Guess a letter", "خمن حرفًا") if action == "hangman_modal" else (self.tr("Word challenge","تحدي الكتابة") if action=="modal" else "Wordle"))
            label = (self.tr("Enter one letter","أدخل حرفًا واحدًا") if action == "hangman_modal" else (self.tr("Type the requested text","اكتب النص المطلوب") if action=="modal" else self.tr("Your 5-letter guess","توقعك من 5 أحرف")))
            return await interaction.response.send_modal(TextEntryModal(self,title,label))
        if action=="memory_ready":
            s["stage"]="answer"; s["options"]=["🔴","🔵","🟢","🟡"]; s["picked"]=""
            self.clear_actions(); self.set_prompt(self.tr("Repeat the sequence in order. Select each color; press Submit when done.","أعد التسلسل بالترتيب. اختر كل لون ثم اضغط إرسال."))
            for i,em in enumerate(s["options"]): self.add_action(em,f"memory:{em}",row=0)
            self.add_action(self.tr("Submit","إرسال"),"memory_submit","✅",discord.ButtonStyle.success,row=1)
            return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("memory:"):
            s["picked"]+=action.split(":",1)[1]; self.set_prompt(self.tr(f"Sequence: {s['picked']} • {len(s['picked'])}/5",f"التسلسل: {s['picked']} • {len(s['picked'])}/5"))
            return await interaction.response.edit_message(embed=self.embed,view=self)
        if action=="memory_submit": return await self._finish(interaction, "win" if s.get("picked")==s["answer"] else "loss", self.tr("Perfect memory!","ذاكرة ممتازة!") if s.get("picked")==s["answer"] else self.tr("Sequence incorrect.","التسلسل غير صحيح."))
        if action=="click":
            s["count"]+=1
            if s["count"]>=s["target"]: return await self._finish(interaction,"win",self.tr("Lightning-fast clicking!","سرعة مذهلة!"),score=s["count"])
            self._fast_click(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("chair:"):
            chosen=int(action.split(":")[1]); removed=random.randint(1,4)
            if chosen==removed:
                s["lives"]-=1
                if s["lives"]<=0: return await self._finish(interaction,"loss",self.tr("You missed the chair!","لم تلحق بالكرسي!"))
            s["round"]+=1
            if s["round"]>5: return await self._finish(interaction,"win",self.tr("You survived all five music rounds!","نجوت من جولات الموسيقى الخمس!"),score=5)
            self._chairs(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("roulette:"):
            pick=int(action.split(":")[1]); trap=random.randint(1,5)
            if pick==trap:
                s["lives"]-=1
                if s["lives"]<=0: return await self._finish(interaction,"loss",self.tr("The trap caught you.","أمسك بك الفخ."))
            s["round"]+=1
            if s["round"]>5: return await self._finish(interaction,"win",self.tr("You cleared all five chambers!","اجتزت الخانات الخمس!"),score=5)
            self._roulette(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("choice:"):
            i=int(action.split(":")[1]); correct=i==s.get("answer_index")
            if g=="impostor": correct=s["options"][i]==s["correct"]
            if g=="hide_seek": correct=s["options"][i]==s["correct"]
            return await self._finish(interaction,"win" if correct else "loss",self.tr("Correct deduction!","استنتاج صحيح!") if correct else self.tr("Not quite. Better luck next time.","ليس تمامًا. حظًا أوفر."),score=1 if correct else 0)
        if action=="dice":
            you,bot=random.randint(1,6),random.randint(1,6); s["round"]+=1
            if you>bot: s["you"]+=1
            elif bot>you: s["bot"]+=1
            if s["round"]>3 or s["you"]==2 or s["bot"]==2:
                res="win" if s["you"]>s["bot"] else ("draw" if s["you"]==s["bot"] else "loss")
                return await self._finish(interaction,res,self.tr(f"You rolled {you}; Arcade rolled {bot}. Final: {s['you']}–{s['bot']}",f"نتيجتك {you}؛ الآركيد {bot}. النهائي: {s['you']}–{s['bot']}"),score=s["you"])
            self._dice(); self.embed.description+=f"\n\n{self.tr(f'Round result: You {you}, Arcade {bot}',f'نتيجة الجولة: أنت {you}، الآركيد {bot}')}"
            return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("rps:"):
            you=action.split(":")[1]; bot=random.choice(["rock","paper","scissors"]); beats={"rock":"scissors","paper":"rock","scissors":"paper"}
            if you==bot: pass
            elif beats[you]==bot: s["you"]+=1
            else: s["bot"]+=1
            s["round"]+=1
            if s["round"]>3 or s["you"]==2 or s["bot"]==2:
                res="win" if s["you"]>s["bot"] else ("draw" if s["you"]==s["bot"] else "loss")
                return await self._finish(interaction,res,self.tr(f"You: {you} • Arcade: {bot}\nFinal score {s['you']}–{s['bot']}",f"أنت: {you} • الآركيد: {bot}\nالنتيجة {s['you']}–{s['bot']}"),score=s["you"])
            self._rps(); self.embed.description+=f"\n\n{self.tr(f'Last round: {you} vs {bot}',f'الجولة السابقة: {you} ضد {bot}')}"
            return await interaction.response.edit_message(embed=self.embed,view=self)

            if you==bot: pass
            elif beats[you]==bot: s["you"]+=1
            else: s["bot"]+=1
            s["round"]+=1
            if s["round"]>3 or s["you"]==2 or s["bot"]==2:
                res="win" if s["you"]>s["bot"] else ("draw" if s["you"]==s["bot"] else "loss")
                return await self._finish(interaction,res,self.tr(f"You: {you} • Arcade: {bot}\nFinal score {s['you']}–{s['bot']}",f"أنت: {you} • الآركيد: {bot}\nالنتيجة {s['you']}–{s['bot']}"),score=s["you"])
            self._rps(); self.embed.description+=f"\n\n{self.tr(f'Last round: {you} vs {bot}',f'الجولة السابقة: {you} ضد {bot}')}"
            return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("emoji:"):
            idx=int(action.split(":")[1]); ok=s["pool"][idx]==s["target"]
            return await self._finish(interaction,"win" if ok else "loss",self.tr("Found it!","وجدته!") if ok else self.tr("That wasn't the target.","هذا ليس الهدف."),score=1 if ok else 0)
        if action.startswith("color:"):
            ok=action.split(":")[1]==s["target"]
            return await self._finish(interaction,"win" if ok else "loss",self.tr("Color matched!","مطابقة صحيحة!") if ok else self.tr("Wrong color.","لون خاطئ."),score=1 if ok else 0)
        if action.startswith("sort:"):
            n=int(action.split(":")[1]); expected=s["sorted"][s["index"]]
            if n!=expected: return await self._finish(interaction,"loss",self.tr(f"Incorrect. {expected} was the next smallest number.",f"خطأ. الرقم التالي هو {expected}."))
            s["nums"].remove(n); s["index"]+=1
            if s["index"]>=5: return await self._finish(interaction,"win",self.tr("All numbers sorted correctly!","رتبت كل الأرقام بشكل صحيح!"),score=5)
            self._sort(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("letter:"):
            ch=action.split(":")[1]; s["guessed"].add(ch)
            if ch not in s["word"]: s["misses"]+=1
            if all(c in s["guessed"] for c in s["word"]): return await self._finish(interaction,"win",self.tr(f"You solved it: {s['word']}",f"حللت الكلمة: {s['word']}"),score=len(s["word"]))
            if s["misses"]>=6: return await self._finish(interaction,"loss",self.tr(f"The word was {s['word']}.",f"الكلمة كانت {s['word']}"))
            self._hangman(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("ttt:"): return await self._ttt_move(interaction,int(action.split(":")[1]))
        if action.startswith("connect:"): return await self._connect_move(interaction,int(action.split(":")[1]))
        if action.startswith("mine:"):
            idx=int(action.split(":")[1]); s["revealed"].add(idx)
            if idx in s["mines"]: return await self._finish(interaction,"loss",self.tr("Boom! You found a mine.","انفجر لغم! لقد وجدته."))
            if len(s["revealed"]-s["mines"])>=s["safe_needed"]: return await self._finish(interaction,"win",self.tr("You cleared seven safe tiles!","كشفت سبعة مربعات آمنة!"),score=7)
            self._mines(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("bank:"):
            typ=action.split(":")[1]; roll=random.random()
            if typ=="safe": change=max(5,int(s["cash"]*.10))
            elif typ=="balanced": change=int(s["cash"]*.25) if roll<.65 else -int(s["cash"]*.10)
            else: change=int(s["cash"]*.60) if roll<.40 else -int(s["cash"]*.35)
            s["cash"]=max(0,s["cash"]+change); s["round"]+=1
            if s["round"]>3:
                res="win" if s["cash"]>100 else ("draw" if s["cash"]==100 else "loss")
                return await self._finish(interaction,res,self.tr(f"Bank closed. Final balance: {s['cash']} coins.",f"أغلق البنك. رصيدك النهائي: {s['cash']} عملة."),score=s["cash"])
            self._bank(); self.embed.description+=f"\n\n{self.tr(f'Change: {change:+}',f'التغيير: {change:+}')}"
            return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("coin:"):
            choice=action.split(":")[1]; flip=random.choice(["Heads","Tails"]); ok=choice==flip
            return await self._finish(interaction,"win" if ok else "loss",self.tr(f"Coin landed on {flip}.",f"ظهرت العملة على {flip}."),score=1 if ok else 0)
        if action=="spin":
            result=[random.choice(s["symbols"]) for _ in range(3)]; s["spins"]-=1; s["last"]="  ".join(result)
            if len(set(result))==1: s["cash_win"]=s.get("cash_win",0)+1
            if s["spins"]<=0:
                wins=s.get("cash_win",0); res="win" if wins else "loss"
                return await self._finish(interaction,res,self.tr(f"Reels: {s['last']}\nJackpots: {wins}",f"النتيجة: {s['last']}\nالجوائز الكبرى: {wins}"),score=wins)
            self._slots(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if action.startswith("safe:"):
            n=int(action.split(":")[1]); ok=n in s["safe"]
            if not ok:
                s["lives"]-=1
                if s["lives"]<=0: return await self._finish(interaction,"loss",self.tr("You ran out of lives.","انتهت محاولاتك."))
            s["round"]+=1
            if s["round"]>3: return await self._finish(interaction,"win",self.tr("You survived all three rounds!","نجوت من الجولات الثلاث!"),score=3)
            s["safe"]=random.sample(range(1,6),3); self._safe_trap(); return await interaction.response.edit_message(embed=self.embed,view=self)
        return await interaction.response.send_message("Unknown action.",ephemeral=True)

    async def handle_text(self, interaction: discord.Interaction, value: str):
        if interaction.user.id!=self.player_id: return await interaction.response.send_message("هذه الجولة ليست لك.",ephemeral=True)
        if self.finished: return await interaction.response.send_message("انتهت الجولة.",ephemeral=True)
        v=" ".join(value.strip().upper().split()); g=self.game_id
        if g in ("fast_type","text_split","unscramble"):
            ok=v==self.state["answer"]
            return await self._finish(interaction,"win" if ok else "loss",self.tr("Exact match!","إجابة مطابقة!") if ok else self.tr(f"Correct answer: {self.state['answer']}",f"الإجابة الصحيحة: {self.state['answer']}"),score=1 if ok else 0)
        if g=="hangman":
            if len(v)!=1 or not v.isalpha():
                return await interaction.response.send_message(self.tr("Enter one letter only.","أدخل حرفًا واحدًا فقط."),ephemeral=True)
            ch=v
            if ch in self.state["guessed"]:
                return await interaction.response.send_message(self.tr("You already tried that letter.","لقد جربت هذا الحرف."),ephemeral=True)
            self.state["guessed"].add(ch)
            if ch not in self.state["word"]: self.state["misses"]+=1
            if all(c in self.state["guessed"] for c in self.state["word"]):
                return await self._finish(interaction,"win",self.tr(f"You solved it: {self.state['word']}",f"حللت الكلمة: {self.state['word']}"),score=len(self.state["word"]))
            if self.state["misses"]>=6:
                return await self._finish(interaction,"loss",self.tr(f"The word was {self.state['word']}.",f"الكلمة كانت {self.state['word']}"))
            self._hangman(); return await interaction.response.edit_message(embed=self.embed,view=self)
        if g=="wordle":
            if len(v)!=5 or not v.isalpha():
                return await interaction.response.send_message(self.tr("Enter exactly five letters.","أدخل خمسة أحرف بالضبط."),ephemeral=True)
            self.state["guesses"].append(v); self.state["tries"]+=1
            if v==self.state["word"]: return await self._finish(interaction,"win",self.tr("Brilliant! You solved Wordle.","ممتاز! حللت ووردل."),score=6-self.state["tries"])
            if self.state["tries"]>=6: return await self._finish(interaction,"loss",self.tr(f"The word was {self.state['word']}.",f"الكلمة كانت {self.state['word']}"))
            self._wordle(); return await interaction.response.edit_message(embed=self.embed,view=self)

    async def _ttt_move(self, interaction: discord.Interaction, pos: int):
        b=self.state["board"]
        if b[pos]!=" ": return await interaction.response.send_message(self.tr("That square is occupied.","هذا المربع مشغول."),ephemeral=True)
        b[pos]="X"
        if self._winner(b,"X"): return await self._finish(interaction,"win",self.tr("You beat the Arcade bot!","هزمت خصم الآركيد!"),score=1)
        if " " not in b: return await self._finish(interaction,"draw",self.tr("It's a draw.","تعادل."))
        # AI: win if possible, block player, otherwise center/corner/random.
        move=self._best_ttt_move(b,"O")
        if move is not None: b[move]="O"
        if self._winner(b,"O"): return await self._finish(interaction,"loss",self.tr("The Arcade bot got three in a row.","خصم الآركيد كوّن ثلاثة متتالية."))
        if " " not in b: return await self._finish(interaction,"draw",self.tr("It's a draw.","تعادل."))
        self._ttt(); return await interaction.response.edit_message(embed=self.embed,view=self)
    @staticmethod
    def _winner(board: list[str], mark: str) -> bool:
        lines=((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))
        return any(all(board[i]==mark for i in line) for line in lines)
    def _best_ttt_move(self, board: list[str], mark: str) -> int | None:
        for candidate in ("O","X"):
            for i,v in enumerate(board):
                if v==" ":
                    board[i]=candidate; won=self._winner(board,candidate); board[i]=" "
                    if won: return i
        for i in (4,0,2,6,8,1,3,5,7):
            if board[i]==" ": return i
        return None

    async def _connect_move(self, interaction: discord.Interaction, col: int):
        b=self.state["board"]
        row=next((r for r in range(5,-1,-1) if b[r][col]==" "),None)
        if row is None: return await interaction.response.send_message(self.tr("That column is full.","هذا العمود ممتلئ."),ephemeral=True)
        b[row][col]="R"
        if self._connect_winner("R"): return await self._finish(interaction,"win",self.tr("Four connected! You win.","أربع قطع متصلة! فزت."),score=1)
        choices=[c for c in range(7) if b[0][c]==" "]
        if not choices: return await self._finish(interaction,"draw",self.tr("Board full — draw.","امتلأت اللوحة — تعادل."))
        # AI prioritizes a winning move, then blocks, otherwise chooses a valid column.
        bot_col=self._connect_tactical("Y")
        if bot_col is None: bot_col=self._connect_tactical("R")
        if bot_col is None: bot_col=random.choice(choices)
        bot_row=next(r for r in range(5,-1,-1) if b[r][bot_col]==" "); b[bot_row][bot_col]="Y"
        if self._connect_winner("Y"): return await self._finish(interaction,"loss",self.tr("The Arcade bot connected four.","خصم الآركيد وصل أربع قطع."))
        if all(b[0][c]!=" " for c in range(7)): return await self._finish(interaction,"draw",self.tr("Board full — draw.","امتلأت اللوحة — تعادل."))
        self._connect(); return await interaction.response.edit_message(embed=self.embed,view=self)
    def _connect_tactical(self, mark: str) -> int | None:
        for c in range(7):
            r=next((r for r in range(5,-1,-1) if self.state["board"][r][c]==" "),None)
            if r is not None:
                self.state["board"][r][c]=mark; won=self._connect_winner(mark); self.state["board"][r][c]=" "
                if won: return c
        return None
    def _connect_winner(self, mark: str) -> bool:
        b=self.state["board"]
        for r in range(6):
            for c in range(7):
                if c+3<7 and all(b[r][c+i]==mark for i in range(4)): return True
                if r+3<6 and all(b[r+i][c]==mark for i in range(4)): return True
                if r+3<6 and c+3<7 and all(b[r+i][c+i]==mark for i in range(4)): return True
                if r+3<6 and c-3>=0 and all(b[r+i][c-i]==mark for i in range(4)): return True
        return False

    async def _finish(self, interaction: discord.Interaction, result: str, detail: str, score: int = 0):
        if self.finished: return await interaction.response.send_message("انتهت الجولة بالفعل.",ephemeral=True)
        self.finished=True
        for item in self.children: item.disabled=True
        xp, coins = {"win":(25,15),"draw":(12,5),"loss":(8,0)}[result]
        try:
            record_game_result(guild_id=self.guild_id,user_id=self.player_id,username=interaction.user.display_name,language=self.lang,game_id=self.game_id,result=result,xp_reward=xp,coin_reward=coins,score=max(0,int(score)))
            heading={"win":self.tr("🏆 Victory!","🏆 فوز!"),"draw":self.tr("🤝 Draw!","🤝 تعادل!"),"loss":self.tr("🎮 Round complete","🎮 انتهت الجولة")}[result]
            desc=f"{detail}\n\n{self.tr(f'Rewards: +{xp} XP • +{coins} coins',f'المكافآت: +{xp} خبرة • +{coins} عملة')}"
            e=build_embed(heading,desc,{"win":GREEN,"draw":GOLD,"loss":RED}[result])
            e.add_field(name=self.tr("Game","اللعبة"),value=game_label(self.game_id,self.lang),inline=True)
            e.add_field(name=self.tr("Player","اللاعب"),value=interaction.user.mention,inline=True)
            await interaction.response.edit_message(embed=e,view=self)
        except Exception:
            log.exception("Could not save result for %s",self.game_id)
            await interaction.response.edit_message(embed=build_embed(self.tr("Result not saved","لم تُحفظ النتيجة"),self.tr("The round ended, but the database could not save it. Please contact an admin.","انتهت الجولة لكن تعذر حفظ النتيجة. يرجى إبلاغ الإدارة."),RED),view=self)
        self.stop()

    async def on_timeout(self):
        if self.finished: return
        self.finished=True
        for item in self.children: item.disabled=True
        if self.message:
            try: await self.message.edit(embed=build_embed(self.tr("⏰ Time's up","⏰ انتهى الوقت"),self.tr("No result was recorded because the round timed out.","لم تُسجل نتيجة لانتهاء الوقت."),RED),view=self)
            except (discord.NotFound,discord.HTTPException): pass


class ArcadeGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot=bot
        self.cooldown=GameCooldown()

    @app_commands.command(name="arcade",description="Open the MHN ARCADE V2.0 games menu.")
    @app_commands.guild_only()
    async def arcade(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("Use this command inside a server.",ephemeral=True)
        left=self.cooldown.remaining(interaction.user.id)
        if left>0:
            return await interaction.response.send_message(f"Please wait {left:.1f}s before reopening the arcade.",ephemeral=True)
        self.cooldown.update(interaction.user.id)
        lang=get_language(interaction.guild.id,interaction.user.id)
        desc=("أهلًا بك في صالة MHN ARCADE!\n\n🏆 المنافسة والتحديات\n⚡ السرعة وردة الفعل\n🧠 الذكاء والألغاز\n🎲 الحظ والاستراتيجية\n\nاختر فئة للبدء." if lang=="ar" else "Welcome to MHN ARCADE!\n\n🏆 Social & Competition\n⚡ Speed & Reflex\n🧠 Brain & Puzzle\n🎲 Luck & Strategy\n\nChoose a category to begin.")
        await interaction.response.send_message(embed=build_embed("💜 MHN ARCADE V2.0",desc),view=ArcadeHomeView(interaction.user.id,interaction.guild.id,lang),ephemeral=True)

    @app_commands.command(name="arcade_stats",description="View your arcade game statistics.")
    @app_commands.guild_only()
    async def arcade_stats(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("Use this command inside a server.",ephemeral=True)
        lang=get_language(interaction.guild.id,interaction.user.id)
        try:
            rows=get_game_stats(interaction.guild.id,interaction.user.id)
            if not rows:
                return await interaction.response.send_message("لم تلعب أي لعبة بعد." if lang=="ar" else "You haven't played any games yet.",ephemeral=True)
            total=sum(int(r["games_played"]) for r in rows)
            wins=sum(int(r["wins"]) for r in rows)
            losses=sum(int(r["losses"]) for r in rows)
            draws=sum(int(r["draws"]) for r in rows)
            lines=[]
            for row in rows[:10]:
                gid=row["game_id"]; label=game_label(gid,lang) if gid in GAMES else gid
                emoji=GAMES[gid]["emoji"] if gid in GAMES else "🎮"
                lines.append(f"{emoji} **{label}** — {row['games_played']} | 🏆 {row['wins']}")
            e=build_embed("📊 إحصائيات الآركيد" if lang=="ar" else "📊 Arcade Statistics","\n".join(lines))
            e.add_field(name="🎮 Games",value=str(total),inline=True)
            e.add_field(name="🏆 Wins",value=str(wins),inline=True)
            e.add_field(name="❌ Losses",value=str(losses),inline=True)
            e.add_field(name="🤝 Draws",value=str(draws),inline=True)
            await interaction.response.send_message(embed=e,ephemeral=True)
        except Exception:
            log.exception("Could not load arcade statistics")
            await interaction.response.send_message("تعذر تحميل الإحصائيات حاليًا." if lang=="ar" else "Could not load statistics right now.",ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ArcadeGames(bot))
    log.info("MHN ARCADE V2.0 Games Engine loaded")
