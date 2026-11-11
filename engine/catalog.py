"""
MHN ARCADE V3 - Default Game Catalog

Registers the initial game definitions supported by V3.

Game metadata is stored here.
Game mechanics are connected through handler factories.
"""

from __future__ import annotations

from typing import Any

from .registry import (
    GameDefinition,
    GameMode,
    GameRegistry,
)


# =========================================================
# GAME HANDLER FACTORIES
# =========================================================

def create_musical_roulette_handler(
    *,
    session: Any,
    session_manager: Any,
    definition: GameDefinition | None = None,
) -> Any:
    """
    Create a Musical Roulette handler.

    Imports the handler lazily to avoid unnecessary
    imports while the catalog is being loaded.
    """

    from .games.musical_roulette import MusicalRoulette

    return MusicalRoulette(
        session=session,
        session_manager=session_manager,
    )

def create_coin_flip_handler(
    *,
    player_id: str,
    player_name: str,
    metadata: Any = None,
    definition: GameDefinition | None = None,
) -> Any:
    """
    Create a Coin Flip handler.
    """

    from .games.coin_flip import CoinFlip

    return CoinFlip(
        player_id=player_id,
        player_name=player_name,
        metadata=metadata,
        definition=definition,
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
        handler_factory=create_coin_flip_handler,
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
        max_players=30,
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
        tags=(
            "multiplayer",
            "elimination",
            "party",
            "competitive",
        ),
        handler_factory=create_musical_roulette_handler,
    ),
)


# =========================================================
# CATALOG BUILDER
# =========================================================

def build_default_registry() -> GameRegistry:
    """
    Build and return a registry containing the default V3 games.
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
    Return a summary of registered game modes.
    """

    return {
        "total": registry.count,
        "single_player": len(registry.single_player_games()),
        "multiplayer": len(registry.multiplayer_games()),
    }
