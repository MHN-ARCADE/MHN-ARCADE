
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from engine.i18n import (
    ARABIC_ARCADE_CHANNEL_ID,
    ENGLISH_ARCADE_CHANNEL_ID,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
    normalize_language,
    resolve_language,
    t,
)


class LanguageNormalizationTests(unittest.TestCase):

    def test_supported_languages(self):
        self.assertEqual(SUPPORTED_LANGUAGES, ("ar", "en"))

    def test_arabic_language(self):
        self.assertEqual(normalize_language("ar"), "ar")

    def test_english_language(self):
        self.assertEqual(normalize_language("en"), "en")

    def test_invalid_language_uses_default(self):
        self.assertEqual(
            normalize_language("fr"),
            DEFAULT_LANGUAGE,
        )

    def test_none_uses_default(self):
        self.assertEqual(
            normalize_language(None),
            DEFAULT_LANGUAGE,
        )


class TranslationTests(unittest.TestCase):

    def test_all_translation_entries_support_both_languages(self):
        for key, translations in TRANSLATIONS.items():
            with self.subTest(key=key):
                self.assertIn("ar", translations)
                self.assertIn("en", translations)
                self.assertTrue(translations["ar"])
                self.assertTrue(translations["en"])

    def test_arabic_translation(self):
        self.assertEqual(
            t("previous", "ar"),
            "السابق",
        )

    def test_english_translation(self):
        self.assertEqual(
            t("previous", "en"),
            "Previous",
        )

    def test_unknown_key_returns_key(self):
        self.assertEqual(
            t("unknown_translation_key", "ar"),
            "unknown_translation_key",
        )

    def test_invalid_language_uses_default_translation(self):
        self.assertEqual(
            t("previous", "fr"),
            t("previous", DEFAULT_LANGUAGE),
        )


class LanguageResolutionTests(unittest.TestCase):

    def make_interaction(self, channel_id):
        return SimpleNamespace(
            channel_id=channel_id,
            guild=SimpleNamespace(id=123),
            user=SimpleNamespace(id=456),
        )

    def test_arabic_channel_forces_arabic(self):
        interaction = self.make_interaction(
            ARABIC_ARCADE_CHANNEL_ID
        )

        with patch(
            "engine.i18n.get_player",
            return_value={"active_language": "en"},
        ):
            self.assertEqual(
                resolve_language(interaction),
                "ar",
            )

    def test_english_channel_forces_english(self):
        interaction = self.make_interaction(
            ENGLISH_ARCADE_CHANNEL_ID
        )

        with patch(
            "engine.i18n.get_player",
            return_value={"active_language": "ar"},
        ):
            self.assertEqual(
                resolve_language(interaction),
                "en",
            )

    def test_saved_player_language_is_used_outside_arcade_channels(self):
        interaction = self.make_interaction(999999)

        with patch(
            "engine.i18n.get_player",
            return_value={"active_language": "ar"},
        ):
            self.assertEqual(
                resolve_language(interaction),
                "ar",
            )

    def test_default_language_when_player_has_no_saved_language(self):
        interaction = self.make_interaction(999999)

        with patch(
            "engine.i18n.get_player",
            return_value=None,
        ):
            self.assertEqual(
                resolve_language(interaction),
                DEFAULT_LANGUAGE,
            )

    def test_database_error_falls_back_to_default(self):
        interaction = self.make_interaction(999999)

        with patch(
            "engine.i18n.get_player",
            side_effect=RuntimeError("Database unavailable"),
        ):
            self.assertEqual(
                resolve_language(interaction),
                DEFAULT_LANGUAGE,
            )


if __name__ == "__main__":
    unittest.main()
