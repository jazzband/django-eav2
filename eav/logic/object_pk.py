import uuid
from functools import partial
from typing import Type

from django.conf import settings
from django.db import models

#: Constants
_DEFAULT_CHARFIELD_LEN: int = 40

_FIELD_MAPPING = {
    "django.db.models.UUIDField": partial(
        models.UUIDField,
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
    ),
    "django.db.models.CharField": partial(
        models.CharField,
        primary_key=True,
        editable=False,
        max_length=_DEFAULT_CHARFIELD_LEN,
    ),
}


def get_pk_format() -> Type[models.Field]:
    """
    Get the primary key field format based on the Django settings.

    This function returns a field factory function that corresponds to the
    primary key format specified in Django settings. If the primary key
    format is not recognized, it defaults to using BigAutoField.

    Returns:
        Type[models.Field]: A field factory function that can be used to
        create the primary key field instance.
    """
    field_factory = _FIELD_MAPPING.get(
        settings.EAV2_PRIMARY_KEY_FIELD,
        partial(models.BigAutoField, primary_key=True, editable=False),
    )

    # Create and return the field instance
    return field_factory()
