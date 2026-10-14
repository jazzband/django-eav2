"""The compiled translations that ship in the package match their sources."""

from __future__ import annotations

from pathlib import Path

import polib
import pytest

_LOCALE_DIR = Path(__file__).parent.parent / "eav" / "locale"
_CATALOGS = sorted(_LOCALE_DIR.glob("*/LC_MESSAGES/django.po"))


def _messages(catalog: polib.POFile | polib.MOFile) -> dict[str, str]:
    return {entry.msgid: entry.msgstr for entry in catalog if entry.msgstr}


@pytest.mark.parametrize("source", _CATALOGS, ids=lambda path: path.parts[-3])
def test_compiled_catalog_matches_its_source(source: Path) -> None:
    compiled = source.with_suffix(".mo")

    assert compiled.exists(), f"Run `compilemessages`: {compiled} is missing"
    assert _messages(polib.mofile(str(compiled))) == _messages(
        polib.pofile(str(source)),
    ), f"Run `compilemessages`: {compiled} is out of date"
