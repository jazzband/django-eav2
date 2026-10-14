from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

import eav
from eav.fields import CSVField
from eav.forms import CSVFormField
from eav.models import Attribute, Value
from eav.widgets import CSVWidget
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


def test_csv_field_deconstructs_a_custom_separator() -> None:
    assert "separator" not in CSVField().deconstruct()[3]
    assert CSVField(separator=",").deconstruct()[3]["separator"] == ","


def test_csv_field_formfield_and_serialization() -> None:
    assert isinstance(CSVField().formfield(), CSVFormField)
    assert CSVField().get_prep_value("a;b") == "a;b"
    assert CSVField().get_prep_value(5) == 5


def test_csv_field_value_to_string() -> None:
    eav.register(Patient)
    Attribute.objects.create(name="tags", datatype=Attribute.TYPE_CSV)
    patient = Patient.objects.create(name="Joe", eav__tags=["a", "b"])
    eav_value = Value.objects.get(entity_id=patient.pk)

    assert Value._meta.get_field("value_csv").value_to_string(eav_value) == "a;b"


@pytest.mark.parametrize(
    ("raw", "rendered"),
    [(None, ""), ("", ""), ("[]", ""), ("a;b", "a;b"), (["a", "b"], "a;b")],
)
def test_csv_widget_prepares_values(raw, rendered) -> None:
    assert CSVWidget().prep_value(raw) == rendered


def test_csv_widget_rejects_other_types() -> None:
    with pytest.raises(ValidationError):
        CSVWidget().prep_value(5)


def test_csv_widget_renders_and_reads_values() -> None:
    widget = CSVWidget()

    assert "a;b" in widget.render("tags", ["a", "b"])
    assert widget.value_from_datadict(
        {"x": SimpleNamespace(tags=["a"])},
        {},
        "tags",
    ) == [
        "a",
    ]
    assert widget.value_from_datadict({"x": SimpleNamespace()}, {}, "tags") is None
