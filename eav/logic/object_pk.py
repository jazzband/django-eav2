from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from functools import partial
from types import MappingProxyType
from typing import Any, Final

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

_BIG_AUTO_FIELD: Final = "django.db.models.BigAutoField"

_FieldFactory = Callable[[], "models.Field[Any, Any]"]

_FIELD_MAPPING: Final[Mapping[str, _FieldFactory]] = MappingProxyType(
    {
        _BIG_AUTO_FIELD: partial(
            models.BigAutoField,
            primary_key=True,
            editable=False,
            serialize=False,
        ),
        "django.db.models.UUIDField": partial(
            models.UUIDField,
            primary_key=True,
            editable=False,
            serialize=False,
            default=uuid.uuid4,
        ),
    },
)


def get_pk_format() -> models.Field[Any, Any]:
    """
    Get the primary key field of the EAV models, from ``EAV2_PRIMARY_KEY_FIELD``.

    The setting may be ``django.db.models.BigAutoField`` (the default when it is
    not set) or ``django.db.models.UUIDField``. It is read by the models and by
    the migrations, so choose it before the first ``migrate``: changing it for
    tables that already exist is not supported.

    Returns:
        models.Field: A new primary key field instance.

    Raises:
        ImproperlyConfigured: If the setting has any other value.
    """
    key_format = getattr(settings, "EAV2_PRIMARY_KEY_FIELD", _BIG_AUTO_FIELD)

    try:
        field_factory = _FIELD_MAPPING[key_format]
    except KeyError as err:
        choices = ", ".join(_FIELD_MAPPING)
        raise ImproperlyConfigured(
            f"EAV2_PRIMARY_KEY_FIELD must be one of {choices}, not {key_format!r}.",
        ) from err

    return field_factory()
