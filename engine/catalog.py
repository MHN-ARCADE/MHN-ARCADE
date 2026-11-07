
"""
MHN ARCADE V3 - Default Game Catalog

Registers the initial game definitions supported by V3.

This module contains metadata only.
Actual game mechanics are implemented separately.
"""

from __future__ import annotations

from .registry import (
    GameDefinition,
    GameMode,
    GameRegistry,
)


# =========================================================
# DEFAULT GAME DEFINITIONS
# =========================================================

DEFAULT_GAMES: tuple[GameDefinition, ...] = (

    # -----------------------------------------------------
    # SINGLE PLAYER
    # -----------------------------------------------------

    GameDefinition(
        game_id="coin_flip",
        name_en="Coin Flip",
        name_ar="رمي العملة",
        mode=GameMode.SINGLE_PLAYER,
        min_players=1,
        max_players=1,
        description_en="A simple heads or tails game.",
        description_ar="لعبة بسيطة لاختيار الصورة أو الكتابة.",
        tags=("classic", "quick", "single-player"),
    ),

    # -----------------------------------------------------
    # MULTIPLAYER
    # -----------------------------------------------------

    GameDefinition(
        game_id="musical_roulette",
        name_en="Musical Roulette",
        name_ar="الروليت الموسيقي",
        mode=GameMode.MULTIPLAYER,
        min_players=3,
        max_players=12,
        description_en=(
            "A multiplayer elimination game. "
            "The selected player chooses another player to eliminate. "
            "The last remaining player wins."
        ),
        description_ar=(
            "لعبة إقصاء جماعية. "
            "يختار اللاعب المحدد لاعباً آخر لإقصائه، "
            "وآخر لاعب متبقٍ يفوز."
        ),
        tags=("multiplayer", "elimination", "party", "competitive"),
    ),
)


# =========================================================
# CATALOG BUILDER
# =========================================================

def build_default_registry() -> GameRegistry:
    """
    Build and return a registry containing the default V3 games.

    Returns:
        GameRegistry: A ready-to-use game registry.
    """

    registry = GameRegistry()

    for definition in DEFAULT_GAMES:
        registry.register(definition)

    return registry


# =========================================================
# REGISTRY SUMMARY
# =========================================================

def get_catalog_summary(
    registry: GameRegistry,
) -> dict[str, int]:
    """
    Return a simple summary of registered game modes.
    """

    return {
        "total": registry.count,
        "single_player": len(registry.single_player_games()),
        "multiplayer": len(registry.multiplayer_games()),
    }
