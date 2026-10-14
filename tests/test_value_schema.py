"""The database schema of the Value model."""

from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from eav.models import Attribute, Value
from test_project.models import Patient

pytestmark = pytest.mark.django_db

_ATTRIBUTE_INDEXES = (
    "eav_value_attr_int_idx",
    "eav_value_attr_float_idx",
    "eav_value_attr_date_idx",
    "eav_value_attr_enum_idx",
)

_LARGE_ID = 3_000_000_000


def test_value_columns_have_attribute_indexes() -> None:
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "eav_value")

    indexes = {name for name, info in constraints.items() if info["index"]}

    assert set(_ATTRIBUTE_INDEXES) <= indexes


def test_entity_and_object_ids_can_be_very_large() -> None:
    attribute = Attribute.objects.create(name="owner", datatype=Attribute.TYPE_INT)
    eav_value = Value(
        attribute=attribute,
        entity_ct=ContentType.objects.get_for_model(Patient),
        entity_id=_LARGE_ID,
        generic_value_id=_LARGE_ID,
        value_int=1,
    )

    eav_value.save()

    stored = Value.objects.get(pk=eav_value.pk)
    assert stored.entity_id == _LARGE_ID
    assert stored.generic_value_id == _LARGE_ID
