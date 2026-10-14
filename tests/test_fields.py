from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

import eav
from eav.fields import CSVField
from eav.models import Attribute
from test_project.models import Patient

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("raw", [None, "", []])
def test_csv_field_treats_empty_values_as_empty_list(raw) -> None:
    field = CSVField()

    assert field.to_python(raw) == []
    assert field.from_db_value(raw, None, None) == []


def test_csv_field_splits_with_its_separator() -> None:
    field = CSVField(separator=",")

    assert field.to_python("a,b") == ["a", "b"]
    assert field.get_prep_value(["a", "b"]) == "a,b"


def test_empty_csv_attribute_round_trips_as_empty_list() -> None:
    eav.register(Patient)
    Attribute.objects.create(name="tags", datatype=Attribute.TYPE_CSV)
    patient = Patient.objects.create(name="Joe", eav__tags=["a", "b"])

    patient.eav.tags = []
    patient.save()

    assert Patient.objects.get(pk=patient.pk).eav.tags == []


def test_datatype_cannot_change_once_in_use() -> None:
    eav.register(Patient)
    attribute = Attribute.objects.create(name="age", datatype=Attribute.TYPE_INT)
    Patient.objects.create(name="Joe", eav__age=3)

    attribute.datatype = Attribute.TYPE_TEXT

    with pytest.raises(ValidationError):
        attribute.full_clean()
