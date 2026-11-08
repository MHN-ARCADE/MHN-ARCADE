
"""
MHN ARCADE V3 - Discord Integration Tests

Tests for:
- Safe text truncation
- Game catalog pagination
- Empty game catalogs
- Discord embed field limits
- Catalog navigation controls
- Catalog interaction ownership
"""

import unittest

from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from discord import Embed

from engine.registry import GameDefinition, GameMode

from v3_discord import (
    GAMES_PER_PAGE,
    CatalogView,
    build_catalog_pages,
    safe_text,
    setup,
    teardown,
)


def make_test_games(count: int) -> tuple:
    """Create sample game definitions for testing."""

    return tuple(
        GameDefinition(
            game_id=f"test_game_{index}",
            name_en=f"Test Game {index}",
            name_ar=f"لعبة اختبار {index}",
            mode=GameMode.SINGLE_PLAYER,
            min_players=1,
            max_players=1,
            description_en="A test game description.",
        )
        for index in range(count)
    )


class DiscordIntegrationTests(unittest.TestCase):

    def test_safe_text_keeps_short_text(self):
        result = safe_text("MHN ARCADE", 50)

        self.assertEqual(result, "MHN ARCADE")

    def test_safe_text_truncates_long_text(self):
        result = safe_text("A" * 100, 20)

        self.assertEqual(len(result), 20)
        self.assertTrue(result.endswith("..."))

    def test_empty_catalog_creates_one_embed(self):
        pages = build_catalog_pages(())

        self.assertEqual(len(pages), 1)
        self.assertIsInstance(pages[0], Embed)
        self.assertEqual(len(pages[0].fields), 0)

    def test_catalog_pagination(self):
        games = make_test_games(9)

        pages = build_catalog_pages(games)

        self.assertEqual(len(pages), 3)

        self.assertEqual(
            [len(page.fields) for page in pages],
            [4, 4, 1],
        )

    def test_catalog_page_limit(self):
        games = make_test_games(20)

        pages = build_catalog_pages(games)

        for page in pages:
            self.assertLessEqual(
                len(page.fields),
                GAMES_PER_PAGE,
            )

    def test_embed_field_limits(self):
        games = make_test_games(10)

        pages = build_catalog_pages(games)

        for page in pages:
            for field in page.fields:
                self.assertLessEqual(
                    len(field.name),
                    256,
                )

                self.assertLessEqual(
                    len(field.value),
                    1024,
                )

    def test_catalog_page_footer(self):
        games = make_test_games(9)

        pages = build_catalog_pages(games)

        self.assertIn("Page 1/3", pages[0].footer.text)
        self.assertIn("Page 2/3", pages[1].footer.text)
        self.assertIn("Page 3/3", pages[2].footer.text)

    def test_catalog_view_navigation_buttons(self):
        pages = build_catalog_pages(
            make_test_games(9)
        )

        view = CatalogView(
            pages=pages,
            owner_id=123456,
        )

        self.assertTrue(
            view.previous_button.disabled
        )

        self.assertFalse(
            view.next_button.disabled
        )

        view.current_page = 2
        view.update_buttons()

        self.assertFalse(
            view.previous_button.disabled
        )

        self.assertTrue(
            view.next_button.disabled
        )

        view.stop()

    def test_catalog_view_single_page_buttons(self):
        pages = build_catalog_pages(
            make_test_games(2)
        )

        view = CatalogView(
            pages=pages,
            owner_id=123456,
        )

        self.assertTrue(
            view.previous_button.disabled
        )

        self.assertTrue(
            view.next_button.disabled
        )

        view.stop()


class DiscordOwnershipTests(unittest.IsolatedAsyncioTestCase):

    async def test_only_owner_can_control_catalog(self):
        pages = build_catalog_pages(
            make_test_games(5)
        )

        view = CatalogView(
            pages=pages,
            owner_id=123456,
        )

        interaction = SimpleNamespace(
            user=SimpleNamespace(id=999999),
            response=SimpleNamespace(
                send_message=AsyncMock()
            ),
        )

        allowed = await view.interaction_check(
            interaction
        )

        self.assertFalse(allowed)

        interaction.response.send_message.assert_awaited_once()

        view.stop()

    async def test_owner_can_control_catalog(self):
        pages = build_catalog_pages(
            make_test_games(5)
        )

        view = CatalogView(
            pages=pages,
            owner_id=123456,
        )

        interaction = SimpleNamespace(
            user=SimpleNamespace(id=123456),
            response=SimpleNamespace(
                send_message=AsyncMock()
            ),
        )

        allowed = await view.interaction_check(
            interaction
        )

        self.assertTrue(allowed)

        interaction.response.send_message.assert_not_awaited()

        view.stop()


if __name__ == "__main__":
    unittest.main()
