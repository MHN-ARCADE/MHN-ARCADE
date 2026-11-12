
"""MHN ARCADE V3 - PNG player card renderer.

Rendering only: this module does not access or modify player data.
The caller supplies values read from the existing V3 runtime and profile.
"""

from __future__ import annotations

import io
import os
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps, features


CARD_WIDTH = 1200
CARD_HEIGHT = 720
BACKGROUND = (18, 13, 32)
PANEL = (31, 23, 52)
PANEL_ALT = (39, 29, 65)
TEXT = (247, 243, 255)
MUTED = (184, 174, 205)
PURPLE = (124, 58, 237)

RANK_ACCENTS: dict[str, tuple[int, int, int]] = {
    "ROOKIE": (100, 116, 139),
    "APPRENTICE": (34, 197, 94),
    "PRO": (59, 130, 246),
    "ELITE": (6, 182, 212),
    "MASTER": (245, 158, 11),
    "MANAGER": (239, 68, 68),
    "GRANDMASTER": (168, 85, 247),
    "MYTHIC": (249, 115, 22),
}

ARABIC_RANKS = {
    "ROOKIE": "مبتدئ",
    "APPRENTICE": "متدرب",
    "PRO": "محترف",
    "ELITE": "إيليت",
    "MASTER": "ماستر",
    "MANAGER": "مانجر",
    "GRANDMASTER": "جراند ماستر",
    "MYTHIC": "ميثيك",
}


def _font_path(bold: bool = False) -> str:
    configured = os.getenv("MHN_ARCADE_FONT_PATH")
    candidates = [configured] if configured else []

    candidates.extend(
        [
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        ]
    )

    for candidate in candidates:
        if candidate:
            try:
                ImageFont.truetype(candidate, 20)
                return candidate
            except OSError:
                continue

    raise RuntimeError(
        "No usable TrueType font was found. Install DejaVu Sans or set "
        "MHN_ARCADE_FONT_PATH to a font file that supports Arabic and English."
    )


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _font_path(bold)

    try:
        return ImageFont.truetype(
            path,
            size,
            layout_engine=ImageFont.Layout.RAQM,
        )
    except (AttributeError, OSError):
        return ImageFont.truetype(path, size)


def _rounded(
    draw: ImageDraw.ImageDraw,
    box,
    radius: int,
    fill,
    outline=None,
    width=1,
):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: Any,
    size: int,
    fill=TEXT,
    bold: bool = False,
    language: str = "en",
    anchor: str | None = None,
) -> None:
    value = str(value)
    options: dict[str, Any] = {}

    if language == "ar":
        if not features.check("raqm"):
            raise RuntimeError(
                "Arabic PNG cards require Pillow built with libraqm support."
            )

        options["direction"] = "rtl"
        options["language"] = "ar"

    draw.text(
        xy,
        value,
        font=_font(size, bold),
        fill=fill,
        anchor=anchor,
        **options,
    )


def _fit_image(
    image_bytes: bytes | None,
    box: tuple[int, int],
    *,
    contain: bool = True,
):
    if not image_bytes:
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            image = source.convert("RGBA")

        if contain:
            image.thumbnail(box, Image.Resampling.LANCZOS)
            return image

        return ImageOps.fit(
            image,
            box,
            method=Image.Resampling.LANCZOS,
        )

    except (OSError, ValueError):
        return None


def _base(
    data: dict[str, Any],
) -> tuple[
    Image.Image,
    ImageDraw.ImageDraw,
    str,
    tuple[int, int, int],
]:
    language = "ar" if data.get("language") == "ar" else "en"
    rank = str(data.get("rank", "ROOKIE")).upper()
    accent = RANK_ACCENTS.get(rank, PURPLE)

    image = Image.new(
        "RGB",
        (CARD_WIDTH, CARD_HEIGHT),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(image)

    for y in range(CARD_HEIGHT):
        blend = y / max(1, CARD_HEIGHT - 1)

        color = (
            int(24 - 8 * blend),
            int(15 - 2 * blend),
            int(43 + 16 * blend),
        )

        draw.line(
            (0, y, CARD_WIDTH, y),
            fill=color,
        )

    draw.ellipse(
        (890, -310, 1450, 250),
        fill=(37, 22, 68),
    )
    draw.ellipse(
        (-260, 510, 250, 1020),
        fill=(29, 20, 53),
    )

    _rounded(
        draw,
        (28, 28, 1172, 692),
        34,
        fill=(23, 17, 40),
        outline=accent,
        width=4,
    )
    _rounded(
        draw,
        (48, 48, 1152, 672),
        26,
        fill=PANEL,
    )
    _rounded(
        draw,
        (48, 48, 1152, 58),
        5,
        fill=accent,
    )

    return image, draw, language, accent


def _paste_avatar(
    image: Image.Image,
    avatar_bytes: bytes | None,
    box: tuple[int, int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    size = min(x2 - x1, y2 - y1)

    avatar = _fit_image(
        avatar_bytes,
        (size, size),
        contain=False,
    )

    if avatar is None:
        return

    mask = Image.new("L", (size, size), 0)

    ImageDraw.Draw(mask).ellipse(
        (0, 0, size - 1, size - 1),
        fill=255,
    )

    image.paste(
        avatar,
        (x1, y1),
        mask,
    )


def _paste_character(
    image: Image.Image,
    character_bytes: bytes | None,
    box: tuple[int, int, int, int],
) -> bool:
    """Place source character artwork without filters or cropping."""

    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1

    artwork = _fit_image(
        character_bytes,
        (width, height),
        contain=True,
    )

    if artwork is None:
        return False

    px = x1 + (width - artwork.width) // 2
    py = y1 + (height - artwork.height) // 2

    image.paste(
        artwork,
        (px, py),
        artwork,
    )

    return True


def _progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    percentage: float,
    accent,
) -> None:
    _rounded(
        draw,
        (x, y, x + width, y + 18),
        9,
        fill=(57, 48, 76),
    )

    fill_width = max(
        0,
        min(
            width,
            int(
                width
                * max(0.0, min(100.0, percentage))
                / 100
            ),
        ),
    )

    if fill_width:
        _rounded(
            draw,
            (x, y, x + fill_width, y + 18),
            9,
            fill=accent,
        )


def render_xp_card_png(
    data: dict[str, Any],
    *,
    avatar_bytes: bytes | None = None,
    character_bytes: bytes | None = None,
) -> bytes:
    """Render the compact XP/level card as PNG bytes."""

    image, draw, language, accent = _base(data)
    is_ar = language == "ar"

    rank = str(data.get("rank", "ROOKIE")).upper()
    rank_label = ARABIC_RANKS.get(rank, rank) if is_ar else rank

    level = int(data.get("level", 1))
    total_xp = int(data.get("total_xp", 0))
    current_xp = int(data.get("current_xp", 0))
    required_xp = max(
        1,
        int(data.get("required_xp", 1)),
    )

    percentage = max(
        0.0,
        min(100.0, current_xp * 100 / required_xp),
    )

    _paste_avatar(
        image,
        avatar_bytes,
        (82, 92, 190, 200),
    )

    _text(
        draw,
        (220, 100),
        data.get("player_name", "Player"),
        38,
        bold=True,
        language=language,
    )

    _text(
        draw,
        (220, 157),
        "بطاقة الخبرة والمستوى"
        if is_ar else "XP & LEVEL CARD",
        22,
        fill=MUTED,
        language=language,
    )

    _rounded(
        draw,
        (820, 92, 1098, 190),
        22,
        fill=PANEL_ALT,
        outline=accent,
        width=2,
    )

    _text(
        draw,
        (959, 112),
        rank_label,
        28,
        fill=accent,
        bold=True,
        language=language,
        anchor="mm",
    )

    _text(
        draw,
        (959, 157),
        f"LEVEL {level}",
        21,
        bold=True,
        language="en",
        anchor="mm",
    )

    _rounded(
        draw,
        (82, 244, 405, 610),
        24,
        fill=(25, 19, 43),
        outline=(77, 61, 103),
        width=2,
    )

    has_character = _paste_character(
        image,
        character_bytes,
        (98, 260, 389, 594),
    )

    if not has_character:
        fallback = (
            "لم يتم اختيار صورة"
            if is_ar
            else "CHARACTER ART UNAVAILABLE"
        )

        _text(
            draw,
            (243, 425),
            fallback,
            20,
            fill=MUTED,
            language=language,
            anchor="mm",
        )

    _text(
        draw,
        (450, 255),
        "الشخصية المختارة"
        if is_ar else "SELECTED CHARACTER",
        18,
        fill=MUTED,
        bold=True,
        language=language,
    )

    _text(
        draw,
        (450, 292),
        data.get(
            "character_name",
            "غير محددة" if is_ar else "Not selected",
        ),
        28,
        bold=True,
        language=language,
    )

    _rounded(
        draw,
        (438, 350, 1098, 610),
        22,
        fill=PANEL_ALT,
    )

    _text(
        draw,
        (478, 385),
        "إجمالي الخبرة"
        if is_ar else "TOTAL EXPERIENCE",
        18,
        fill=MUTED,
        bold=True,
        language=language,
    )

    _text(
        draw,
        (478, 430),
        f"{total_xp:,} XP",
        42,
        bold=True,
        language="en",
    )

    _text(
        draw,
        (478, 505),
        "التقدم للمستوى التالي"
        if is_ar else "NEXT LEVEL PROGRESS",
        17,
        fill=MUTED,
        bold=True,
        language=language,
    )

    _progress_bar(
        draw,
        478,
        545,
        560,
        percentage,
        accent,
    )

    _text(
        draw,
        (478, 579),
        f"{current_xp:,} / {required_xp:,} XP  •  {percentage:.0f}%",
        17,
        fill=TEXT,
        language="en",
    )

    _text(
        draw,
        (600, 640),
        "MHN ARCADE",
        17,
        fill=MUTED,
        bold=True,
        language="en",
        anchor="mm",
    )

    output = io.BytesIO()
    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()


def render_player_card_png(
    data: dict[str, Any],
    *,
    avatar_bytes: bytes | None = None,
    character_bytes: bytes | None = None,
) -> bytes:
    """Render the full player card as PNG bytes."""

    image, draw, language, accent = _base(data)
    is_ar = language == "ar"

    rank = str(data.get("rank", "ROOKIE")).upper()
    rank_label = ARABIC_RANKS.get(rank, rank) if is_ar else rank

    _paste_avatar(
        image,
        avatar_bytes,
        (82, 84, 190, 192),
    )

    _text(
        draw,
        (220, 91),
        data.get("player_name", "Player"),
        36,
        bold=True,
        language=language,
    )

    username = str(data.get("username", ""))

    _text(
        draw,
        (220, 145),
        username,
        18,
        fill=MUTED,
        language="en",
    )

    _rounded(
        draw,
        (820, 82, 1098, 184),
        22,
        fill=PANEL_ALT,
        outline=accent,
        width=2,
    )

    _text(
        draw,
        (959, 108),
        rank_label,
        27,
        fill=accent,
        bold=True,
        language=language,
        anchor="mm",
    )

    _text(
        draw,
        (959, 151),
        f"LEVEL {int(data.get('level', 1))}",
        20,
        bold=True,
        language="en",
        anchor="mm",
    )

    _rounded(
        draw,
        (82, 220, 390, 642),
        24,
        fill=(25, 19, 43),
        outline=(77, 61, 103),
        width=2,
    )

    if not _paste_character(
        image,
        character_bytes,
        (98, 236, 374, 626),
    ):
        _text(
            draw,
            (236, 430),
            "لا توجد صورة" if is_ar else "NO CHARACTER IMAGE",
            20,
            fill=MUTED,
            language=language,
            anchor="mm",
        )

    _text(
        draw,
        (410, 220),
        data.get(
            "character_name",
            "غير محددة" if is_ar else "Not selected",
        ),
        24,
        bold=True,
        language=language,
    )

    _rounded(
        draw,
        (410, 266, 1098, 404),
        20,
        fill=PANEL_ALT,
    )

    _text(
        draw,
        (446, 290),
        "إجمالي XP" if is_ar else "TOTAL XP",
        16,
        fill=MUTED,
        bold=True,
        language=language,
    )

    _text(
        draw,
        (446, 326),
        f"{int(data.get('total_xp', 0)):,}",
        34,
        bold=True,
        language="en",
    )

    _text(
        draw,
        (740, 290),
        "تقدم المستوى"
        if is_ar else "LEVEL PROGRESS",
        16,
        fill=MUTED,
        bold=True,
        language=language,
    )

    current_xp = int(data.get("current_xp", 0))
    required_xp = max(
        1,
        int(data.get("required_xp", 1)),
    )

    percentage = max(
        0.0,
        min(100.0, current_xp * 100 / required_xp),
    )

    _text(
        draw,
        (740, 326),
        f"{current_xp:,} / {required_xp:,} XP",
        22,
        bold=True,
        language="en",
    )

    _progress_bar(
        draw,
        740,
        365,
        310,
        percentage,
        accent,
    )

    stats = [
        (
            (410, 430, 620, 520),
            "المباريات" if is_ar else "GAMES",
            data.get("games", 0),
        ),
        (
            (636, 430, 846, 520),
            "الانتصارات" if is_ar else "WINS",
            data.get("wins", 0),
        ),
        (
            (862, 430, 1098, 520),
            "الخسائر" if is_ar else "LOSSES",
            data.get("losses", 0),
        ),
        (
            (410, 540, 620, 630),
            "نسبة الفوز" if is_ar else "WIN RATE",
            f"{float(data.get('win_rate', 0.0)):.1f}%",
        ),
        (
            (636, 540, 846, 630),
            "الإنجازات" if is_ar else "ACHIEVEMENTS",
            data.get("achievements", 0),
        ),
        (
            (862, 540, 1098, 630),
            "أفضل سلسلة" if is_ar else "BEST STREAK",
            data.get("best_streak", 0),
        ),
    ]

    for box, label, value in stats:
        _rounded(
            draw,
            box,
            16,
            fill=PANEL_ALT,
        )

        x1, y1, x2, y2 = box

        _text(
            draw,
            ((x1 + x2) // 2, y1 + 23),
            label,
            14,
            fill=MUTED,
            bold=True,
            language=language,
            anchor="mm",
        )

        _text(
            draw,
            ((x1 + x2) // 2, y1 + 61),
            value,
            25,
            bold=True,
            language="en",
            anchor="mm",
        )

    # Wallet values are included only when real values are supplied.
    if data.get("coins") is not None or data.get("bank") is not None:
        wallet_text = (
            f"المحفظة: {int(data.get('coins') or 0):,}  •  البنك: {int(data.get('bank') or 0):,}"
            if is_ar
            else f"WALLET: {int(data.get('coins') or 0):,}  •  BANK: {int(data.get('bank') or 0):,}"
        )

        _text(
            draw,
            (600, 657),
            wallet_text,
            14,
            fill=MUTED,
            language=language,
            anchor="mm",
        )

    else:
        _text(
            draw,
            (600, 657),
            "MHN ARCADE",
            15,
            fill=MUTED,
            bold=True,
            language="en",
            anchor="mm",
        )

    output = io.BytesIO()
    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()
