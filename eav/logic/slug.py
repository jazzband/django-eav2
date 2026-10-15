from __future__ import annotations

import secrets
import string
from typing import Final

from django.utils.text import slugify

SLUGFIELD_MAX_LENGTH: Final = 50
_FALLBACK_CHARS: Final = string.ascii_lowercase + string.digits


def non_identifier_chars() -> dict[str, str]:
    """Generate a mapping of non-identifier characters to their Unicode representations.

    Returns:
        dict[str, str]: A dictionary where keys are special characters and values
            are their Unicode representations.
    """
    # Start with all printable characters
    all_chars = string.printable

    # Filter out characters that are valid in Python identifiers
    special_chars = [
        char for char in all_chars if not char.isalnum() and char not in ["_", " "]
    ]

    return {char: f"u{ord(char):04x}" for char in special_chars}


_NON_IDENTIFIER_CHARS: Final = non_identifier_chars()


def generate_slug(text: str) -> str:
    """Generate a valid slug based on the given text.

    This function converts the input text into a Python-identifier-friendly slug.
    It handles special characters, ensures a valid Python identifier, and truncates
    the result to fit within the maximum allowed length.

    Args:
        text (str): The input string to generate a slug from.

    Returns:
        str: A valid Python identifier slug, with a maximum
            length of SLUGFIELD_MAX_LENGTH.
    """
    for char, replacement in _NON_IDENTIFIER_CHARS.items():
        text = text.replace(char, replacement)

    # Use slugify to create a URL-friendly base slug.
    slug = slugify(text, allow_unicode=False).replace("-", "_")

    # If slugify returns an empty string, generate a fallback
    # slug to ensure it's never empty.
    if not slug:
        suffix = "".join(secrets.choice(_FALLBACK_CHARS) for _ in range(8))
        slug = f"rand_{suffix}"

    # Ensure the slug doesn't start with a digit to make it a valid Python identifier.
    if slug[0].isdigit():
        slug = f"_{slug}"

    return slug[:SLUGFIELD_MAX_LENGTH]
