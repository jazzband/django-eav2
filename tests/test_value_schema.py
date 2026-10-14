"""The database schema of the Value model."""

from __future__ import annotations

import pytest
from django.db import connection

pytestmark = pytest.mark.django_db

_ATTRIBUTE_INDEXES = (
    "eav_value_attr_int_idx",
    "eav_value_attr_float_idx",
    "eav_value_attr_date_idx",
    "eav_value_attr_enum_idx",
)


def test_value_columns_have_attribute_indexes() -> None:
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "eav_value")

    indexes = {name for name, info in constraints.items() if info["index"]}

    assert set(_ATTRIBUTE_INDEXES) <= indexes
