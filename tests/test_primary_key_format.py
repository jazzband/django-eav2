import uuid

from django.db import models

from eav.logic.object_pk import _DEFAULT_CHARFIELD_LEN, get_pk_format


def test_get_uuid_primary_key(settings) -> None:
    settings.EAV2_PRIMARY_KEY_FIELD = "django.db.models.UUIDField"
    primary_field = get_pk_format()
    assert isinstance(primary_field, models.UUIDField)
    assert primary_field.primary_key
    assert not primary_field.editable
    assert primary_field.default == uuid.uuid4


def test_get_char_primary_key(settings) -> None:
    settings.EAV2_PRIMARY_KEY_FIELD = "django.db.models.CharField"
    primary_field = get_pk_format()
    assert isinstance(primary_field, models.CharField)
    assert primary_field.primary_key
    assert not primary_field.editable
    assert primary_field.max_length == _DEFAULT_CHARFIELD_LEN


def test_get_default_primary_key(settings) -> None:
    # This test covers the default case for "BigAutoField"
    settings.EAV2_PRIMARY_KEY_FIELD = "AnyOtherField"
    primary_field = get_pk_format()
    assert isinstance(primary_field, models.BigAutoField)
    assert primary_field.primary_key
    assert not primary_field.editable
