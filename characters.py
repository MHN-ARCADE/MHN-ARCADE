"""
========================================================
MHN ARCADE V2.0
Character Collection System 💜
27 Characters - Anime & Netflix
========================================================
"""

from copy import deepcopy


# ========================================================
# CHARACTER CATEGORIES
# ========================================================

CATEGORY_ANIME = "anime"
CATEGORY_NETFLIX = "netflix"

GENDER_MALE = "male"
GENDER_FEMALE = "female"


# ========================================================
# CHARACTER CATALOG
# ========================================================

CHARACTERS = {

    # ====================================================
    # ANIME - MALE
    # ====================================================

    "gojo": {
        "id": "gojo",
        "name": "Satoru Gojo",
        "name_ar": "ساتورو غوجو",
        "series": "Jujutsu Kaisen",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The strongest sorcerer.",
        "description_ar": "أقوى ساحر.",
    },

    "sukuna": {
        "id": "sukuna",
        "name": "Ryomen Sukuna",
        "name_ar": "ريومن سوكونا",
        "series": "Jujutsu Kaisen",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The King of Curses.",
        "description_ar": "ملك اللعنات.",
    },

    "levi": {
        "id": "levi",
        "name": "Levi Ackerman",
        "name_ar": "ليفاى أكرمان",
        "series": "Attack on Titan",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "Humanity's strongest soldier.",
        "description_ar": "أقوى جندي للبشرية.",
    },

    "goku": {
        "id": "goku",
        "name": "Son Goku",
        "name_ar": "سون غوكو",
        "series": "Dragon Ball",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The Saiyan warrior.",
        "description_ar": "محارب السايان.",
    },

    "aizen": {
        "id": "aizen",
        "name": "Sosuke Aizen",
        "name_ar": "سوسكي آيزن",
        "series": "Bleach",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The master manipulator.",
        "description_ar": "العقل المدبر.",
    },

    "urahara": {
        "id": "urahara",
        "name": "Kisuke Urahara",
        "name_ar": "كيسكي أوراهارا",
        "series": "Bleach",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The mysterious shopkeeper.",
        "description_ar": "صاحب المتجر الغامض.",
    },

    "ichigo": {
        "id": "ichigo",
        "name": "Ichigo Kurosaki",
        "name_ar": "إيتشيغو كوروساكي",
        "series": "Bleach",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The Substitute Soul Reaper.",
        "description_ar": "الشينيغامي البديل.",
    },

    "toji": {
        "id": "toji",
        "name": "Toji Fushiguro",
        "name_ar": "توجي فوشيغورو",
        "series": "Jujutsu Kaisen",
        "category": CATEGORY_ANIME,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The Sorcerer Killer.",
        "description_ar": "قاتل السحرة.",
    },


    # ====================================================
    # ANIME - FEMALE
    # ====================================================

    "mikasa": {
        "id": "mikasa",
        "name": "Mikasa Ackerman",
        "name_ar": "ميكاسا أكرمان",
        "series": "Attack on Titan",
        "category": CATEGORY_ANIME,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The elite soldier.",
        "description_ar": "الجندية النخبة.",
    },

    "nezuko": {
        "id": "nezuko",
        "name": "Nezuko Kamado",
        "name_ar": "نيزوكو كامادو",
        "series": "Demon Slayer",
        "category": CATEGORY_ANIME,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The demon girl.",
        "description_ar": "الفتاة الشيطانية.",
    },

    "makima": {
        "id": "makima",
        "name": "Makima",
        "name_ar": "ماكيما",
        "series": "Chainsaw Man",
        "category": CATEGORY_ANIME,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The mysterious Control Devil.",
        "description_ar": "شيطانة السيطرة الغامضة.",
    },

    "sakura": {
        "id": "sakura",
        "name": "Sakura Haruno",
        "name_ar": "ساكورا هارونو",
        "series": "Naruto",
        "category": CATEGORY_ANIME,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The skilled medical ninja.",
        "description_ar": "النينجا الطبية الماهرة.",
    },

    "nami": {
        "id": "nami",
        "name": "Nami",
        "name_ar": "نامي",
        "series": "One Piece",
        "category": CATEGORY_ANIME,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The Straw Hat navigator.",
        "description_ar": "ملاحة طاقم قبعة القش.",
    },

    "zero_two": {
        "id": "zero_two",
        "name": "Zero Two",
        "name_ar": "زيرو تو",
        "series": "Darling in the Franxx",
        "category": CATEGORY_ANIME,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The mysterious pilot.",
        "description_ar": "الطيارة الغامضة.",
    },

    "maki": {
        "id": "maki",
        "name": "Maki Zenin",
        "name_ar": "ماكي زينين",
        "series": "Jujutsu Kaisen",
        "category": CATEGORY_ANIME,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The powerful Zenin warrior.",
        "description_ar": "محاربة عائلة زينين.",
    },


    # ====================================================
    # NETFLIX - MALE
    # ====================================================

    "geralt": {
        "id": "geralt",
        "name": "Geralt of Rivia",
        "name_ar": "جيرالت أوف ريفيا",
        "series": "The Witcher",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The legendary monster hunter.",
        "description_ar": "صائد الوحوش الأسطوري.",
    },

    "berlin": {
        "id": "berlin",
        "name": "Berlin",
        "name_ar": "برلين",
        "series": "Money Heist",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The elegant strategist.",
        "description_ar": "المخطط الأنيق.",
    },

    "professor": {
        "id": "professor",
        "name": "The Professor",
        "name_ar": "البروفيسور",
        "series": "Money Heist",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The mastermind behind the plan.",
        "description_ar": "العقل المدبر للخطة.",
    },

    "steve": {
        "id": "steve",
        "name": "Steve Harrington",
        "name_ar": "ستيف هارينغتون",
        "series": "Stranger Things",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The brave babysitter.",
        "description_ar": "الحامي الشجاع.",
    },

    "eddie": {
        "id": "eddie",
        "name": "Eddie Munson",
        "name_ar": "إيدي مونسون",
        "series": "Stranger Things",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The metalhead hero.",
        "description_ar": "بطل الميتال.",
    },

    "joe": {
        "id": "joe",
        "name": "Joe Goldberg",
        "name_ar": "جو غولدبيرغ",
        "series": "You",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_MALE,
        "image_url": None,
        "description": "The mysterious bookstore manager.",
        "description_ar": "مدير المكتبة الغامض.",
    },


    # ====================================================
    # NETFLIX - FEMALE
    # ====================================================

    "wednesday": {
        "id": "wednesday",
        "name": "Wednesday Addams",
        "name_ar": "وينزداي آدامز",
        "series": "Wednesday",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The dark and clever student.",
        "description_ar": "الطالبة الذكية والغامضة.",
    },

    "eleven": {
        "id": "eleven",
        "name": "Eleven",
        "name_ar": "إليفن",
        "series": "Stranger Things",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The girl with extraordinary powers.",
        "description_ar": "الفتاة ذات القوى الخارقة.",
    },

    "nairobi": {
        "id": "nairobi",
        "name": "Nairobi",
        "name_ar": "نايروبي",
        "series": "Money Heist",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The fearless team leader.",
        "description_ar": "قائدة الفريق الشجاعة.",
    },

    "yennefer": {
        "id": "yennefer",
        "name": "Yennefer of Vengerberg",
        "name_ar": "ينيفر أوف فينغربيرغ",
        "series": "The Witcher",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The powerful sorceress.",
        "description_ar": "الساحرة القوية.",
    },

    "enola": {
        "id": "enola",
        "name": "Enola Holmes",
        "name_ar": "إينولا هولمز",
        "series": "Enola Holmes",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The clever young detective.",
        "description_ar": "المحققة الشابة الذكية.",
    },

    "beth": {
        "id": "beth",
        "name": "Beth Harmon",
        "name_ar": "بيث هارمون",
        "series": "The Queen's Gambit",
        "category": CATEGORY_NETFLIX,
        "gender": GENDER_FEMALE,
        "image_url": None,
        "description": "The chess prodigy.",
        "description_ar": "عبقرية الشطرنج.",
    },
}


# ========================================================
# CATEGORY HELPERS
# ========================================================

def get_character(character_id):
    """Return a character by ID, or None."""

    character = CHARACTERS.get(str(character_id).lower())

    if character is None:
        return None

    return deepcopy(character)


def get_all_characters():
    """Return all characters."""

    return [deepcopy(character) for character in CHARACTERS.values()]


def get_characters_by_category(category):
    """Return characters from anime or Netflix."""

    return [
        deepcopy(character)
        for character in CHARACTERS.values()
        if character["category"] == category
    ]


def get_characters_by_gender(gender):
    """Return characters by gender."""

    return [
        deepcopy(character)
        for character in CHARACTERS.values()
        if character["gender"] == gender
    ]


def get_characters_by_series(series):
    """Return characters belonging to a specific series."""

    normalized = str(series).strip().lower()

    return [
        deepcopy(character)
        for character in CHARACTERS.values()
        if character["series"].lower() == normalized
    ]


# ========================================================
# CHARACTER COUNTS
# ========================================================

def get_character_count():
    return len(CHARACTERS)


def get_category_count(category):
    return len(get_characters_by_category(category))


def get_gender_count(gender):
    return len(get_characters_by_gender(gender))


def get_character_statistics():

    return {
        "total": len(CHARACTERS),

        "anime": get_category_count(CATEGORY_ANIME),
        "netflix": get_category_count(CATEGORY_NETFLIX),

        "male": get_gender_count(GENDER_MALE),
        "female": get_gender_count(GENDER_FEMALE),
    }


# ========================================================
# CHARACTER SEARCH
# ========================================================

def search_characters(query):

    query = str(query).strip().lower()

    if not query:
        return []

    results = []

    for character in CHARACTERS.values():

        searchable = (
            character["id"],
            character["name"],
            character["name_ar"],
            character["series"],
            character["description"],
            character["description_ar"],
        )

        if any(query in str(value).lower() for value in searchable):
            results.append(deepcopy(character))

    return results


# ========================================================
# CHARACTER IMAGE HELPERS
# ========================================================

def get_character_image(character_id):

    character = get_character(character_id)

    if character is None:
        return None

    return character.get("image_url")


def set_character_image(character_id, image_url):

    """
    Update the image URL in runtime memory.

    This does not permanently save image URLs.
    The final image catalog will be connected
    to the bot configuration in a later update.
    """

    character_id = str(character_id).lower()

    if character_id not in CHARACTERS:
        return False

    if image_url is not None:
        image_url = str(image_url).strip()

        if not image_url.startswith(("https://", "http://")):
            raise ValueError("Image URL must use HTTP or HTTPS.")

    CHARACTERS[character_id]["image_url"] = image_url

    return True


# ========================================================
# DISCORD SELECT OPTION DATA
# ========================================================

def get_character_select_data(category, language="en"):

    """
    Returns character data suitable for Discord select menus.

    Discord select menus allow up to 25 options.
    Each category currently contains fewer than 25.
    """

    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language.")

    characters = get_characters_by_category(category)

    options = []

    for character in characters:

        if language == "ar":
            label = character["name_ar"]
            description = character["series"]
        else:
            label = character["name"]
            description = character["series"]

        options.append({
            "value": character["id"],
            "label": label[:100],
            "description": description[:100],
        })

    return options


# ========================================================
# LANGUAGE CONSTANTS
# ========================================================

SUPPORTED_LANGUAGES = ("ar", "en")


# ========================================================
# VALIDATION
# ========================================================

def validate_character_catalog():

    expected = {
        "total": 27,
        "anime": 15,
        "netflix": 12,
        "male": 14,
        "female": 13,
    }

    actual = get_character_statistics()

    for key, expected_value in expected.items():

        if actual[key] != expected_value:
            raise RuntimeError(
                f"Character catalog error: {key} "
                f"expected {expected_value}, got {actual[key]}"
            )

    return True


validate_character_catalog()
