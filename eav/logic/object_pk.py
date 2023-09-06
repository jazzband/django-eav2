import uuid

from functools import partial
from django.db import models
from django.conf import settings


def get_pk_format():
    PrimaryField = partial(models.BigAutoField, primary_key=True, editable=False)
    if settings.PRIMARY_KEY_TYPE == "UUID":
        PrimaryField = partial(
            models.UUIDField, primary_key=True, editable=False, default=uuid.uuid4
        )
    return PrimaryField()
