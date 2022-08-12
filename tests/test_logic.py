from hypothesis import given
from hypothesis import strategies as st

from eav.logic.slug import SLUGFIELD_MAX_LENGTH, generate_slug


@given(st.text())
def test_generate_slug(name: str) -> None:
    """Ensures slug generation works properly."""
    slug = generate_slug(name)

    assert slug


@given(st.text(min_size=SLUGFIELD_MAX_LENGTH))
def test_generate_long_slug_text(name: str) -> None:
    """Ensures a slug isn't generated longer than maximum allowed length."""
    slug = generate_slug(name)

    assert len(slug) <= SLUGFIELD_MAX_LENGTH
