from __future__ import annotations

import pytest
from django.db.utils import NotSupportedError

import eav
from eav.models import Attribute
from test_project.models import Doctor, ExampleModel, Patient

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.filterwarnings("ignore::eav.exceptions.RemovedInEav3Warning"),
]


@pytest.fixture(autouse=True)
def _register_models() -> None:
    eav.register(Patient)
    eav.register(ExampleModel)


@pytest.fixture
def age() -> Attribute:
    return Attribute.objects.create(name="age", datatype=Attribute.TYPE_INT)


def _names(queryset) -> list[str]:
    return list(queryset.values_list("name", flat=True))


def test_order_by_on_uuid_primary_key(age: Attribute) -> None:
    for name, years in (("a", 5), ("b", 2), ("c", 9)):
        Doctor.objects.create(name=name, eav__age=years)

    assert _names(Doctor.objects.order_by("eav__age")) == ["b", "a", "c"]


def test_order_by_on_empty_queryset(age: Attribute) -> None:
    assert _names(Patient.objects.order_by("eav__age")) == []
    assert _names(Doctor.objects.order_by("eav__age")) == []


def test_order_by_descending(age: Attribute) -> None:
    for name, years in (("a", 5), ("b", 2), ("c", 9)):
        Patient.objects.create(name=name, eav__age=years)

    assert _names(Patient.objects.order_by("-eav__age")) == ["c", "a", "b"]


def test_order_by_the_same_attribute_twice(age: Attribute) -> None:
    for name, years in (("a", 5), ("b", 2)):
        Patient.objects.create(name=name, eav__age=years)

    ordered = Patient.objects.order_by("eav__age", "-eav__age", "name")

    assert _names(ordered) == ["b", "a"]


def test_order_by_ignores_values_of_other_models(age: Attribute) -> None:
    patient = Patient.objects.create(name="patient", eav__age=1)
    other = Patient.objects.create(name="other", eav__age=5)
    # Same primary key as `patient`, but a different model:
    ExampleModel.objects.create(pk=patient.pk, name="example", eav__age=99)

    assert _names(Patient.objects.order_by("-eav__age")) == [other.name, "patient"]


def test_order_by_object_attribute_is_not_supported() -> None:
    Attribute.objects.create(name="owner", datatype=Attribute.TYPE_OBJECT)

    with pytest.raises(NotSupportedError):
        Patient.objects.order_by("eav__owner")


@pytest.mark.parametrize(
    "lookup",
    [
        lambda: Patient.objects.order_by("eav__missing"),
        lambda: Patient.objects.filter(eav__missing=1),
        lambda: Patient.objects.exclude(eav__missing=1),
    ],
)
def test_unknown_attribute_raises_a_descriptive_error(lookup) -> None:
    with pytest.raises(
        Attribute.DoesNotExist,
        match='Cannot find EAV attribute "missing"',
    ):
        lookup()
