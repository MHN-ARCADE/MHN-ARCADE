
"""MHN ARCADE V3 - Premium unified PNG card renderer.

Both XP and player cards share one visual identity.
Rank accents, player identity, character artwork and V3 statistics
are supplied by the existing runtime. This module only renders PNGs.
"""

from __future__ import annotations

import io
import os
from typing import Any

from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageFont,
    ImageOps,
    features,
)


CARD_WIDTH = 1200
CARD_HEIGHT = 720

BACKGROUND = (12, 13, 29)
PANEL = (20, 23, 43)
PANEL_ALT = (28, 32, 57)
PANEL_LIGHT = (36, 41, 69)

TEXT = (247, 248, 255)
MUTED = (166, 177, 202)
SUBTLE = (111, 124, 153)

PURPLE = (151, 105, 255)

RANK_ACCENTS: dict[str, tuple[int, int, int]] = {
    "ROOKIE": (139, 155, 181),
    "APPRENTICE": (67, 205, 132),
    "PRO": (83, 151, 255),
    "ELITE": (48, 210, 222),
    "MASTER": (255, 190, 75),
    "MANAGER": (255, 105, 112),
    "GRANDMASTER": (190, 119, 255),
    "MYTHIC": (255, 133, 75),
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


# =========================================================
# FONTS AND TEXT
# =========================================================

def _font_path(bold: bool = False) -> str:
    configured = os.getenv("MHN_ARCADE_FONT_PATH")
    candidates = [configured] if configured else []

    candidates.extend([
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        (
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
        ),
    ])

    for candidate in candidates:
        if candidate:
            try:
                ImageFont.truetype(candidate, 20)
                return candidate
            except OSError:
                continue

    raise RuntimeError(
        "No usable TrueType font was found. Install DejaVu Sans "
        "or set MHN_ARCADE_FONT_PATH to a font file."
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


def _text_options(language: str) -> dict[str, Any]:
    if language != "ar":
        return {}

    if not features.check("raqm"):
        raise RuntimeError(
            "Arabic PNG cards require Pillow built with libraqm support."
        )

    return {
        "direction": "rtl",
        "language": "ar",
    }


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: Any,
    size: int,
    *,
    fill=TEXT,
    bold: bool = False,
    language: str = "en",
    anchor: str | None = None,
    max_width: int | None = None,
) -> None:
    value = str(value)
    options = _text_options(language)

    if max_width:
        while size > 12:
            font = _font(size, bold)
            bounds = draw.textbbox(
                (0, 0),
                value,
                font=font,
                **options,
            )

            if bounds[2] - bounds[0] <= max_width:
                break

            size -= 1

    draw.text(
        xy,
        value,
        font=_font(size, bold),
        fill=fill,
        anchor=anchor,
        **options,
    )


def _rank_label(rank: str, language: str) -> str:
    if language == "ar":
        return ARABIC_RANKS.get(rank, rank)

    return rank


# =========================================================
# DRAWING HELPERS
# =========================================================

def _rounded(
    draw: ImageDraw.ImageDraw,
    box,
    radius: int,
    fill,
    outline=None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def _glow(
    image: Image.Image,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    opacity: int = 28,
) -> None:
    """Add a blurred ambient glow behind the card content."""

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(overlay)

    glow_draw.ellipse(
        box,
        fill=(*color, max(0, min(255, opacity))),
    )

    # GaussianBlur is the correct Pillow filter for a soft glow.
    overlay = overlay.filter(
        ImageFilter.GaussianBlur(radius=75)
    )

    image.alpha_composite(overlay)


def _make_base(
    data: dict[str, Any],
) -> tuple[
    Image.Image,
    ImageDraw.ImageDraw,
    str,
    str,
    tuple[int, int, int],
]:
    language = "ar" if data.get("language") == "ar" else "en"
    rank = str(data.get("rank", "ROOKIE")).upper()
    accent = RANK_ACCENTS.get(rank, PURPLE)

    image = Image.new(
        "RGBA",
        (CARD_WIDTH, CARD_HEIGHT),
        (*BACKGROUND, 255),
    )

    # Deep navy-to-purple background gradient.
    pixels = image.load()

    for y in range(CARD_HEIGHT):
        blend = y / max(1, CARD_HEIGHT - 1)

        color = (
            int(13 + 7 * blend),
            int(14 + 2 * blend),
            int(30 + 18 * blend),
            255,
        )

        for x in range(CARD_WIDTH):
            pixels[x, y] = color

    # Decorative rank-colored ambient lighting.
    _glow(
        image,
        (760, -390, 1470, 300),
        accent,
        35,
    )
    _glow(
        image,
        (-330, 400, 330, 1060),
        PURPLE,
        25,
    )

    draw = ImageDraw.Draw(image)

    _rounded(
        draw,
        (22, 22, 1178, 698),
        34,
        fill=(17, 19, 37),
        outline=accent,
        width=3,
    )

    _rounded(
        draw,
        (34, 34, 1166, 686),
        27,
        fill=(19, 22, 42),
        outline=(48, 54, 82),
        width=1,
    )

    _rounded(
        draw,
        (58, 48, 1142, 54),
        3,
        fill=accent,
    )

    draw.line(
        (58, 70, 58, 95),
        fill=accent,
        width=3,
    )
    draw.line(
        (1142, 625, 1142, 650),
        fill=accent,
        width=3,
    )

    return image, draw, language, rank, accent


def _load_image(
    image_bytes: bytes | None,
    box: tuple[int, int],
    *,
    contain: bool,
) -> Image.Image | None:
    if not image_bytes:
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            result = source.convert("RGBA")

        if contain:
            result.thumbnail(
                box,
                Image.Resampling.LANCZOS,
            )
            return result

        return ImageOps.fit(
            result,
            box,
            method=Image.Resampling.LANCZOS,
        )

    except (OSError, ValueError):
        return None


def _paste_avatar(
    image: Image.Image,
    avatar_bytes: bytes | None,
    box: tuple[int, int, int, int],
) -> bool:
    """Paste the member avatar as a circular image."""

    if not avatar_bytes:
        return False

    x1, y1, x2, y2 = box
    size = min(x2 - x1, y2 - y1)

    avatar = _load_image(
        avatar_bytes,
        (size, size),
        contain=False,
    )

    if avatar is None:
        return False

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

    return True


def _paste_character(
    image: Image.Image,
    character_bytes: bytes | None,
    box: tuple[int, int, int, int],
) -> bool:
    """Place character artwork without cropping or recoloring it."""

    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1

    artwork = _load_image(
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


def _paste_character_or_avatar(
    image: Image.Image,
    character_bytes: bytes | None,
    avatar_bytes: bytes | None,
    box: tuple[int, int, int, int],
) -> str:
    """Use character artwork when available, otherwise member avatar."""

    if _paste_character(
        image,
        character_bytes,
        box,
    ):
        return "character"

    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1

    avatar = _load_image(
        avatar_bytes,
        (width, height),
        contain=False,
    )

    if avatar is None:
        return "none"

    mask = Image.new("L", (width, height), 0)

    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=22,
        fill=255,
    )

    image.paste(
        avatar,
        (x1, y1),
        mask,
    )

    return "avatar"


def _draw_portrait_frame(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    accent,
) -> None:
    x1, y1, x2, y2 = box

    _rounded(
        draw,
        (x1 - 7, y1 - 7, x2 + 7, y2 + 7),
        27,
        fill=(24, 28, 50),
        outline=accent,
        width=3,
    )

    _rounded(
        draw,
        (x1 - 2, y1 - 2, x2 + 2, y2 + 2),
        22,
        fill=(10, 13, 27),
        outline=(83, 91, 122),
        width=1,
    )


def _draw_progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    percentage: float,
    accent,
    height: int = 17,
) -> None:
    percentage = max(
        0.0,
        min(100.0, percentage),
    )

    _rounded(
        draw,
        (x, y, x + width, y + height),
        height // 2,
        fill=(48, 55, 81),
    )

    fill_width = int(
        width * percentage / 100
    )

    if fill_width > 0:
        _rounded(
            draw,
            (x, y, x + fill_width, y + height),
            height // 2,
            fill=accent,
        )


def _draw_brand(
    draw: ImageDraw.ImageDraw,
    accent,
    language: str,
) -> None:
    _rounded(
        draw,
        (865, 69, 1135, 119),
        23,
        fill=(25, 35, 65),
        outline=(48, 62, 100),
        width=1,
    )

    _draw_text(
        draw,
        (1000, 94),
        "MHN ARCADE",
        25,
        fill=accent,
        bold=True,
        language="en",
        anchor="mm",
    )


def _draw_rank_badge(
    draw: ImageDraw.ImageDraw,
    rank: str,
    accent,
    language: str,
    box: tuple[int, int, int, int],
) -> None:
    x1, y1, x2, y2 = box

    _rounded(
        draw,
        box,
        21,
        fill=(34, 30, 65),
        outline=accent,
        width=2,
    )

    _draw_text(
        draw,
        ((x1 + x2) // 2, (y1 + y2) // 2),
        _rank_label(rank, language),
        22,
        fill=accent,
        bold=True,
        language=language,
        anchor="mm",
        max_width=(x2 - x1) - 24,
    )


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    accent,
    language: str,
) -> None:
    footer = (
        "رحلتك مستمرة"
        if language == "ar"
        else "YOUR JOURNEY CONTINUES"
    )

    _draw_text(
        draw,
        (600, 670),
        footer,
        15,
        fill=MUTED,
        bold=True,
        language=language,
        anchor="mm",
    )

    draw.ellipse(
        (570, 665, 578, 673),
        fill=accent,
    )


# =========================================================
# SHARED PLAYER IDENTITY
# =========================================================

def _draw_player_identity(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    data: dict[str, Any],
    *,
    avatar_bytes: bytes | None,
    character_bytes: bytes | None,
    language: str,
    rank: str,
    accent,
    xp_card: bool,
) -> None:
    is_ar = language == "ar"

    _draw_brand(
        draw,
        accent,
        language,
    )

    portrait_box = (72, 151, 385, 405)

    _draw_portrait_frame(
        draw,
        portrait_box,
        accent,
    )

    portrait_source = _paste_character_or_avatar(
        image,
        character_bytes,
        avatar_bytes,
        portrait_box,
    )

    if portrait_source == "none":
        fallback = (
            "لا توجد صورة"
            if is_ar
            else "IMAGE UNAVAILABLE"
        )

        _draw_text(
            draw,
            (228, 278),
            fallback,
            19,
            fill=MUTED,
            language=language,
            anchor="mm",
        )

    # Member avatar appears separately as a small identity marker.
    avatar_box = (425, 157, 481, 213)

    _rounded(
        draw,
        (421, 153, 485, 217),
        32,
        fill=(29, 34, 59),
        outline=accent,
        width=2,
    )

    _paste_avatar(
        image,
        avatar_bytes,
        avatar_box,
    )

    player_name = data.get(
        "player_name",
        "Player",
    )

    _draw_text(
        draw,
        (510, 181),
        player_name,
        34,
        bold=True,
        language=language,
        anchor="lm",
        max_width=590,
    )

    username = str(
        data.get("username", "")
    ).strip()

    if username:
        username_label = f"@{username.lstrip('@')}"

        _draw_text(
            draw,
            (510, 224),
            username_label,
            18,
            fill=MUTED,
            language="en",
            anchor="lm",
            max_width=570,
        )

    character_name = data.get(
        "character_name",
        "غير محددة" if is_ar else "Not selected",
    )

    character_label = (
        "الشخصية المختارة"
        if is_ar
        else "SELECTED CHARACTER"
    )

    _draw_text(
        draw,
        (510, 285),
        character_label,
        15,
        fill=SUBTLE,
        bold=True,
        language=language,
    )

    _draw_text(
        draw,
        (510, 322),
        character_name,
        24,
        fill=TEXT,
        bold=True,
        language=language,
        max_width=590,
    )

    level = max(
        1,
        int(data.get("level", 1)),
    )

    _draw_text(
        draw,
        (510, 369),
        f"LEVEL {level}",
        27,
        fill=accent,
        bold=True,
        language="en",
    )

    _draw_rank_badge(
        draw,
        rank,
        accent,
        language,
        (825, 345, 1115, 398),
    )


# =========================================================
# XP CARD
# =========================================================

def render_xp_card_png(
    data: dict[str, Any],
    *,
    avatar_bytes: bytes | None = None,
    character_bytes: bytes | None = None,
) -> bytes:
    """Render the compact XP and level card as PNG bytes."""

    image, draw, language, rank, accent = _make_base(data)
    is_ar = language == "ar"

    total_xp = max(
        0,
        int(data.get("total_xp", 0)),
    )

    current_xp = max(
        0,
        int(data.get("current_xp", 0)),
    )

    required_xp = max(
        1,
        int(data.get("required_xp", 1)),
    )

    percentage = max(
        0.0,
        min(100.0, current_xp * 100 / required_xp),
    )

    _draw_text(
        draw,
        (72, 103),
        "تقدم اللاعب" if is_ar else "PLAYER PROGRESSION",
        25,
        fill=MUTED,
        bold=True,
        language=language,
    )

    _draw_player_identity(
        image,
        draw,
        data,
        avatar_bytes=avatar_bytes,
        character_bytes=character_bytes,
        language=language,
        rank=rank,
        accent=accent,
        xp_card=True,
    )

    draw.line(
        (72, 445, 1128, 445),
        fill=(59, 68, 98),
        width=2,
    )

    _draw_text(
        draw,
        (1120, 483),
        "تقدم المستوى" if is_ar else "LEVEL PROGRESS",
        25,
        fill=TEXT,
        bold=True,
        language=language,
        anchor="ra",
    )

    _draw_text(
        draw,
        (80, 525),
        f"{current_xp:,} / {required_xp:,}",
        27,
        fill=TEXT,
        bold=True,
        language="en",
    )

    _draw_text(
        draw,
        (1120, 525),
        "الخبرة الحالية" if is_ar else "CURRENT XP",
        19,
        fill=MUTED,
        language=language,
        anchor="ra",
    )

    _draw_progress_bar(
        draw,
        72,
        548,
        1056,
        percentage,
        accent,
        height=18,
    )

    panels = [
        (
            (72, 585, 575, 646),
            "المستوى التالي" if is_ar else "NEXT LEVEL",
            f"{max(0, required_xp - current_xp):,} XP",
        ),
        (
            (625, 585, 1128, 646),
            "إجمالي الخبرة" if is_ar else "TOTAL XP",
            f"{total_xp:,}",
        ),
    ]

    for box, label, value in panels:
        _rounded(
            draw,
            box,
            17,
            fill=PANEL_ALT,
            outline=(51, 61, 91),
            width=1,
        )

        x1, y1, x2, y2 = box

        _draw_text(
            draw,
            (x1 + 20, y1 + 17),
            label,
            14,
            fill=MUTED,
            bold=True,
            language=language,
        )

        _draw_text(
            draw,
            (x2 - 20, y1 + 18),
            value,
            23,
            fill=TEXT,
            bold=True,
            language="en",
            anchor="ra",
            max_width=(x2 - x1) - 45,
        )

    _draw_footer(
        draw,
        accent,
        language,
    )

    output = io.BytesIO()

    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()


# =========================================================
# FULL PLAYER CARD
# =========================================================

def render_player_card_png(
    data: dict[str, Any],
    *,
    avatar_bytes: bytes | None = None,
    character_bytes: bytes | None = None,
) -> bytes:
    """Render the full V3 player profile card as PNG bytes."""

    image, draw, language, rank, accent = _make_base(data)
    is_ar = language == "ar"

    _draw_text(
        draw,
        (72, 103),
        "بطاقة اللاعب" if is_ar else "PLAYER PROFILE",
        25,
        fill=MUTED,
        bold=True,
        language=language,
    )

    _draw_player_identity(
        image,
        draw,
        data,
        avatar_bytes=avatar_bytes,
        character_bytes=character_bytes,
        language=language,
        rank=rank,
        accent=accent,
        xp_card=False,
    )

    draw.line(
        (72, 445, 1128, 445),
        fill=(59, 68, 98),
        width=2,
    )

    total_xp = max(
        0,
        int(data.get("total_xp", 0)),
    )

    current_xp = max(
        0,
        int(data.get("current_xp", 0)),
    )

    required_xp = max(
        1,
        int(data.get("required_xp", 1)),
    )

    percentage = max(
        0.0,
        min(100.0, current_xp * 100 / required_xp),
    )

    _draw_text(
        draw,
        (1120, 473),
        "إجمالي الخبرة" if is_ar else "TOTAL EXPERIENCE",
        15,
        fill=MUTED,
        bold=True,
        language=language,
        anchor="ra",
    )

    _draw_text(
        draw,
        (80, 473),
        f"{total_xp:,} XP",
        23,
        fill=TEXT,
        bold=True,
        language="en",
    )

    _draw_progress_bar(
        draw,
        72,
        507,
        1056,
        percentage,
        accent,
        height=13,
    )

    _draw_text(
        draw,
        (1120, 536),
        f"{current_xp:,} / {required_xp:,} XP",
        15,
        fill=MUTED,
        language="en",
        anchor="ra",
    )

    # Five V3 statistics only.
    stats = [
        (
            "المباريات" if is_ar else "GAMES",
            max(0, int(data.get("games", 0))),
        ),
        (
            "الانتصارات" if is_ar else "WINS",
            max(0, int(data.get("wins", 0))),
        ),
        (
            "الخسائر" if is_ar else "LOSSES",
            max(0, int(data.get("losses", 0))),
        ),
        (
            "نسبة الفوز" if is_ar else "WIN RATE",
            f"{max(0.0, float(data.get('win_rate', 0.0))):.1f}%",
        ),
        (
            "الإنجازات" if is_ar else "ACHIEVEMENTS",
            max(0, int(data.get("achievements", 0))),
        ),
    ]

    stat_width = 198
    stat_gap = 16
    total_width = stat_width * 5 + stat_gap * 4
    start_x = (CARD_WIDTH - total_width) // 2

    stat_y1 = 568
    stat_y2 = 646

    for index, (label, value) in enumerate(stats):
        x1 = start_x + index * (stat_width + stat_gap)
        x2 = x1 + stat_width

        box = (
            x1,
            stat_y1,
            x2,
            stat_y2,
        )

        _rounded(
            draw,
            box,
            15,
            fill=PANEL_ALT,
            outline=(48, 57, 86),
            width=1,
        )

        _rounded(
            draw,
            (x1 + 14, stat_y1 + 10, x1 + 42, stat_y1 + 13),
            2,
            fill=accent,
        )

        _draw_text(
            draw,
            ((x1 + x2) // 2, stat_y1 + 31),
            label,
            12,
            fill=MUTED,
            bold=True,
            language=language,
            anchor="mm",
            max_width=stat_width - 20,
        )

        _draw_text(
            draw,
            ((x1 + x2) // 2, stat_y1 + 59),
            value,
            22,
            fill=TEXT,
            bold=True,
            language="en",
            anchor="mm",
            max_width=stat_width - 18,
        )

    _draw_footer(
        draw,
        accent,
        language,
    )

    output = io.BytesIO()

    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()
