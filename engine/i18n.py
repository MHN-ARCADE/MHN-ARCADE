"""
MHN ARCADE V3 - Internationalization

Central language configuration and translations.
Supports Arabic and English Discord interfaces.
"""

from __future__ import annotations

from database import get_player


# =========================================================
# CHANNEL CONFIGURATION
# =========================================================

ARABIC_ARCADE_CHANNEL_ID = 1567665645905121330
ENGLISH_ARCADE_CHANNEL_ID = 1567700330433609910

DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES = ("ar", "en")


# =========================================================
# TRANSLATIONS
# =========================================================

TRANSLATIONS = {
    "catalog_empty": {
        "ar": "لا توجد ألعاب متاحة حاليًا.",
        "en": "No games are currently registered.",
    },
    "catalog_title": {
        "ar": "💜 ألعاب MHN ARCADE V3",
        "en": "💜 MHN ARCADE V3 Games",
    },
    "catalog_description": {
        "ar": "اكتشف ألعاب الجيل الجديد من MHN ARCADE!",
        "en": "Explore the next generation of MHN ARCADE!",
    },
    "game_id": {
        "ar": "معرّف اللعبة",
        "en": "Game ID",
    },
    "game_mode": {
        "ar": "نوع اللعبة",
        "en": "Game Mode",
    },
    "players": {
        "ar": "اللاعبون",
        "en": "Players",
    },
    "previous": {
        "ar": "السابق",
        "en": "Previous",
    },
    "next": {
        "ar": "التالي",
        "en": "Next",
    },
    "owner_only": {
        "ar": "هذه القائمة مخصصة للشخص الذي فتحها.",
        "en": "This menu belongs to the player who opened it.",
    },

    # Coin Flip
    "coin_flip_title": {
        "ar": "🪙 MHN ARCADE V3 • رمي العملة",
        "en": "🪙 MHN ARCADE V3 • Coin Flip",
    },
    "coin_flip_description": {
        "ar": "اضغط الزر لرمي العملة واختبار حظك!",
        "en": "Flip the coin and test your luck!",
    },
    "coin_flip_waiting": {
        "ar": "بانتظار أول رمية...",
        "en": "Waiting for your first flip...",
    },
    "coin_flip_result": {
        "ar": "النتيجة",
        "en": "Result",
    },
    "coin_flip_heads": {
        "ar": "الصورة",
        "en": "Heads",
    },
    "coin_flip_tails": {
        "ar": "الكتابة",
        "en": "Tails",
    },
    "coin_flip_number": {
        "ar": "رقم الرمية",
        "en": "Flip Number",
    },
    "coin_flip_total": {
        "ar": "إجمالي الرميات",
        "en": "Total Flips",
    },
    "coin_flip_button": {
        "ar": "ارمِ العملة",
        "en": "Flip Coin",
    },
    "coin_flip_finished": {
        "ar": "انتهت هذه اللعبة.",
        "en": "This game has ended.",
    },

    # Musical Roulette
    "roulette_title": {
        "ar": "🎵 MHN ARCADE V3 • الروليت الموسيقي",
        "en": "🎵 MHN ARCADE V3 • Musical Roulette",
    },
    "roulette_description": {
        "ar": "انضموا إلى اللوبي واستعدوا للمواجهة!",
        "en": "Join the lobby and get ready to play!",
    },
    "roulette_no_players": {
        "ar": "لا يوجد لاعبون بعد.",
        "en": "No players yet.",
    },
    "roulette_requirements": {
        "ar": "المتطلبات",
        "en": "Requirements",
    },
    "roulette_minimum": {
        "ar": "الحد الأدنى",
        "en": "Minimum",
    },
    "roulette_host": {
        "ar": "المضيف",
        "en": "Host",
    },
    "roulette_join": {
        "ar": "انضمام",
        "en": "Join",
    },
    "roulette_leave": {
        "ar": "مغادرة",
        "en": "Leave",
    },
    "roulette_start": {
        "ar": "ابدأ اللعبة",
        "en": "Start Game",
    },
    "roulette_close": {
        "ar": "إغلاق اللوبي",
        "en": "Close Lobby",
    },
    "roulette_unavailable": {
        "ar": "هذا اللوبي لم يعد متاحًا.",
        "en": "This lobby is no longer available.",
    },
    "roulette_host_only": {
        "ar": "المضيف فقط يستطيع تنفيذ هذا الإجراء.",
        "en": "Only the lobby host can perform this action.",
    },
    "roulette_closed": {
        "ar": "🔒 تم إغلاق اللوبي بواسطة المضيف.",
        "en": "🔒 The lobby was closed by the host.",
    },
    "roulette_wait_turn": {
        "ar": "انتظر دورك! اللاعب المحدد حاليًا هو الذي يختار.",
        "en": "Wait for your turn! The current chooser must select.",
    },
    "roulette_round": {
        "ar": "الجولة",
        "en": "Round",
    },
    "roulette_current_chooser": {
        "ar": "اللاعب الذي يختار",
        "en": "Current Chooser",
    },
    "roulette_choose_player": {
        "ar": "يجب على اللاعب المحدد اختيار لاعب لإقصائه.",
        "en": "The current chooser must select a player to eliminate.",
    },
    "roulette_winner": {
        "ar": "الفائز",
        "en": "Winner",
    },
    "roulette_congratulations": {
        "ar": "🎉 مبروك الفوز!",
        "en": "🎉 Congratulations!",
    },
    "roulette_draw": {
        "ar": "🤝 انتهت اللعبة بالتعادل!",
        "en": "🤝 It's a draw!",
    },
    "roulette_ended": {
        "ar": "انتهت المباراة.",
        "en": "The match has ended.",
    },
    "roulette_remaining": {
        "ar": "اللاعبون المتبقون",
        "en": "Remaining Players",
    },
    "roulette_history": {
        "ar": "سجل الإقصاءات",
        "en": "Elimination History",
    },

    # General errors
    "server_only": {
        "ar": "استخدم هذا الأمر داخل السيرفر.",
        "en": "Use this command inside the server.",
    },
    "generic_error": {
        "ar": "حدث خطأ غير متوقع. حاول مرة أخرى.",
        "en": "An unexpected error occurred. Please try again.",
    },
    "coin_flip_error": {
        "ar": "تعذر تشغيل رمي العملة حاليًا.",
        "en": "Coin Flip is currently unavailable.",
    },
    "catalog_error": {
        "ar": "تعذر تحميل قائمة الألعاب حاليًا.",
        "en": "Could not load the game catalog right now.",
    },
}


# =========================================================
# LANGUAGE RESOLVER
# =========================================================

def normalize_language(language: str | None) -> str:
    """Return a supported language or the default."""

    if language in SUPPORTED_LANGUAGES:
        return language

    return DEFAULT_LANGUAGE


def resolve_language(interaction) -> str:
    """
    Resolve the interface language.

    Priority:
    1. Arabic or English arcade channel.
    2. Saved player language.
    3. Default language.
    """

    channel_id = getattr(interaction, "channel_id", None)

    if channel_id == ARABIC_ARCADE_CHANNEL_ID:
        return "ar"

    if channel_id == ENGLISH_ARCADE_CHANNEL_ID:
        return "en"

    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)

    if guild is not None and user is not None:
        try:
            player = get_player(guild.id, user.id)

            if player is not None:
                saved_language = player["active_language"]

                if saved_language in SUPPORTED_LANGUAGES:
                    return saved_language

        except Exception:
            pass

    return DEFAULT_LANGUAGE


# =========================================================
# TRANSLATION HELPER
# =========================================================

def t(
    key: str,
    language: str = DEFAULT_LANGUAGE,
    **kwargs,
) -> str:
    """Translate a key into Arabic or English."""

    language = normalize_language(language)

    entry = TRANSLATIONS.get(key)

    if entry is None:
        return key

    value = entry.get(
        language,
        entry.get(DEFAULT_LANGUAGE, key),
    )

    try:
        return value.format(**kwargs)
    except (KeyError, ValueError):
        return value
