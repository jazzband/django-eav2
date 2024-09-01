from __future__ import annotations

import secrets
import string
from typing import Final

from django.utils.text import slugify

SLUGFIELD_MAX_LENGTH: Final = 50

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
        char for char in all_chars
        if not char.isalnum() and char not in ["_", " "]
    ]

    return {char: f"u{ord(char):04x}" for char in special_chars}

def generate_slug(value: str) -> str:
    """Generate a valid slug based on the given value.

    This function converts the input value into a Python-identifier-friendly slug.
    It handles special characters, ensures a valid Python identifier, and truncates
    the result to fit within the maximum allowed length.

    Args:
        value (str): The input string to generate a slug from.

    Returns:
        str: A valid Python identifier slug, with a maximum
            length of SLUGFIELD_MAX_LENGTH.
    """
    for char, replacement in non_identifier_chars().items():
        value = value.replace(char, replacement)

    # Use slugify to create a URL-friendly base slug.
    slug = slugify(value, allow_unicode=False).replace("-", "_")

    # If slugify returns an empty string, generate a fallback
    # slug to ensure it's never empty.
    if not slug:
        chars = string.ascii_lowercase + string.digits
        randstr = "".join(secrets.choice(chars) for _ in range(8))
        slug = f"rand_{randstr}"

    # Ensure the slug doesn't start with a digit to make it a valid Python identifier.
    if slug[0].isdigit():
        slug = "_" + slug

    return slug[:SLUGFIELD_MAX_LENGTH]
