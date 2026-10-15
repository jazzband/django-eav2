"""Warnings for features that django-eav2 3.0 removes."""

from __future__ import annotations

import inspect
import os
import warnings
from pathlib import Path
from types import MappingProxyType
from typing import Final

import django

from eav.exceptions import RemovedInEav3Warning

#: Datatypes that django-eav2 3.0 removes, with what to use instead.
DEPRECATED_DATATYPES: Final = MappingProxyType(
    {
        "json": "a JSONField on your model",
        "csv": "a JSONField that holds a list, or a related model",
        "object": "a ForeignKey or a ManyToManyField on your model",
    },
)

# Frames inside these directories are skipped, so the warning points at the
# code that uses django-eav2 and not at our code or at Django's ``create()``.
_EAV_DIR: Final = Path(__file__).resolve().parents[1]
_DJANGO_DIR: Final = Path(django.__file__).resolve().parent
_SKIPPED_DIRS: Final = (f"{_EAV_DIR}{os.sep}", f"{_DJANGO_DIR}{os.sep}")


def warn_if_deprecated_datatype(datatype: str, slug: str) -> None:
    """Warn when *datatype*, used by the attribute *slug*, is one that 3.0 removes."""
    alternative = DEPRECATED_DATATYPES.get(datatype)

    if alternative is None:
        return

    kind, name = repr(datatype), repr(slug)
    message = (
        f"The {kind} datatype of attribute {name} is deprecated and "
        + f"django-eav2 3.0 removes it. Use {alternative} instead."
    )
    warnings.warn(message, RemovedInEav3Warning, stacklevel=_user_stacklevel())


def _user_stacklevel() -> int:
    """Count the frames up to the first one outside of eav and Django."""
    # Level 1 is the ``warnings.warn`` call, and 2 is the caller of our caller.
    level = 2
    frame = inspect.currentframe()
    frame = frame.f_back.f_back if frame and frame.f_back else None

    while frame is not None and frame.f_code.co_filename.startswith(_SKIPPED_DIRS):
        frame = frame.f_back
        level += 1

    return level
