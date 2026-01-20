"""Internationalization (i18n) module for IoT Device Manager."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Translator:
    """Simple JSON-based translation system."""

    _translations: dict = {}
    _language: str = ""
    _initialized: bool = False

    @classmethod
    def initialize(cls, language: str) -> None:
        """Initialize the translator with a language.

        Args:
            language: Language code ("en" or "sv")
        """
        if cls._language == language and cls._initialized:
            return

        cls._language = language
        cls._translations = {}

        # Load translation file
        i18n_dir = Path(__file__).parent
        lang_file = i18n_dir / f"{language}.json"

        if lang_file.exists():
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    cls._translations = json.load(f)
                logger.info(f"Loaded translations for '{language}'")
                cls._initialized = True
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load translations for '{language}': {e}")
                # Fall back to English
                if language != "en":
                    cls.initialize("en")
        else:
            logger.warning(f"Translation file not found: {lang_file}")
            # Fall back to English
            if language != "en":
                cls.initialize("en")

    @classmethod
    def get(cls, key: str, **kwargs) -> str:
        """Get a translated string.

        Args:
            key: Translation key
            **kwargs: Format arguments for the string

        Returns:
            Translated string, or key if not found
        """
        if not cls._initialized:
            return key

        text = cls._translations.get(key, key)

        # Apply format arguments if provided
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass

        return text

    @classmethod
    def get_language(cls) -> str:
        """Get the current language code."""
        return cls._language

    @classmethod
    def get_available_languages(cls) -> list[tuple[str, str]]:
        """Get list of available languages.

        Returns:
            List of (code, name) tuples
        """
        return [
            ("en", "English"),
            ("sv", "Svenska"),
        ]


def _(key: str, **kwargs) -> str:
    """Shortcut function for getting translations.

    Args:
        key: Translation key
        **kwargs: Format arguments

    Returns:
        Translated string
    """
    return Translator.get(key, **kwargs)


def init_translator(language: str) -> None:
    """Initialize the translator with a language.

    Args:
        language: Language code
    """
    Translator.initialize(language)


def get_language() -> str:
    """Get the current language code."""
    return Translator.get_language()


def get_available_languages() -> list[tuple[str, str]]:
    """Get list of available languages."""
    return Translator.get_available_languages()
