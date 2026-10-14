import uuid

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from eav.logic.object_pk import get_pk_format


def test_get_uuid_primary_key(settings) -> None:
    settings.EAV2_PRIMARY_KEY_FIELD = "django.db.models.UUIDField"
    primary_field = get_pk_format()
    assert isinstance(primary_field, models.UUIDField)
    assert primary_field.primary_key
    assert not primary_field.editable
    assert primary_field.default == uuid.uuid4


def test_get_big_auto_primary_key(settings) -> None:
    settings.EAV2_PRIMARY_KEY_FIELD = "django.db.models.BigAutoField"
    primary_field = get_pk_format()
    assert isinstance(primary_field, models.BigAutoField)
    assert primary_field.primary_key
    assert not primary_field.editable


def test_unset_primary_key_setting_defaults_to_big_auto_field(settings) -> None:
    del settings.EAV2_PRIMARY_KEY_FIELD
    assert isinstance(get_pk_format(), models.BigAutoField)


@pytest.mark.parametrize(
    "unsupported",
    [
        "django.db.models.CharField",
        "django.db.models.AutoField",
        "AnyOtherField",
    ],
)
def test_other_primary_key_settings_are_rejected(settings, unsupported) -> None:
    settings.EAV2_PRIMARY_KEY_FIELD = unsupported

    with pytest.raises(ImproperlyConfigured, match="EAV2_PRIMARY_KEY_FIELD"):
        get_pk_format()
