import secrets
import string
from typing import Final

from django.utils.text import slugify

SLUGFIELD_MAX_LENGTH: Final = 50


def generate_slug(name: str) -> str:
    """Generates a valid slug based on ``name``."""
    slug = slugify(name, allow_unicode=False)

    if not slug:
        # Fallback to ensure a slug is always generated by using a random one
        chars = string.ascii_lowercase + string.digits
        randstr = ''.join(secrets.choice(chars) for _ in range(8))
        slug = 'rand-{0}'.format(randstr)

    slug = slug.encode('utf-8', 'surrogateescape').decode()

    return slug[:SLUGFIELD_MAX_LENGTH]
