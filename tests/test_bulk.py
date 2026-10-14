"""Bulk creation and update of entities together with their EAV values."""

from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.utils import NotSupportedError
from django.utils import timezone

import eav
from eav.exceptions import IllegalAssignmentException
from eav.models import Attribute, EnumGroup, EnumValue, Value
from test_project.models import Doctor, Patient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _schema() -> None:
    eav.register(Patient)
    Attribute.objects.create(name="age", datatype=Attribute.TYPE_INT)
    Attribute.objects.create(name="city", datatype=Attribute.TYPE_TEXT)
    Attribute.objects.create(name="dob", datatype=Attribute.TYPE_DATE)
    Attribute.objects.create(name="tags", datatype=Attribute.TYPE_CSV)
    Attribute.objects.create(name="extra", datatype=Attribute.TYPE_JSON)
    yes = EnumValue.objects.create(value="yes")
    no = EnumValue.objects.create(value="no")
    group = EnumGroup.objects.create(name="yes no")
    group.values.add(yes, no)
    Attribute.objects.create(
        name="fever",
        datatype=Attribute.TYPE_ENUM,
        enum_group=group,
    )


def _doctors(count: int) -> list[Doctor]:
    doctors = []
    for number in range(count):
        doctor = Doctor(name=f"d{number}")
        doctor.eav.age = number
        doctor.eav.city = f"city{number}"
        doctors.append(doctor)
    return doctors


def test_bulk_create_stores_values_in_few_queries(
    django_assert_num_queries,
) -> None:
    ContentType.objects.get_for_model(Doctor)

    # The savepoint and its release, the attributes, the doctors, then one
    # upsert per datatype used (int and text).
    with django_assert_num_queries(2 + 1 + 1 + 2):
        Doctor.objects.bulk_create(_doctors(50))

    assert Doctor.objects.count() == 50
    assert Value.objects.count() == 100
    assert Doctor.objects.get(name="d7").eav.age == 7
    assert Doctor.objects.get(name="d7").eav.city == "city7"


def test_bulk_create_with_integer_primary_keys() -> None:
    patients = []
    for number in range(5):
        patient = Patient(name=f"p{number}")
        patient.eav.age = number
        patients.append(patient)

    if not connection.features.can_return_rows_from_bulk_insert:
        # MySQL does not return auto-increment keys, so the values cannot be linked.
        with pytest.raises(NotSupportedError, match="Primary keys are needed"):
            Patient.objects.bulk_create(patients)
        return

    created = Patient.objects.bulk_create(patients)

    assert all(patient.pk is not None for patient in created)
    assert sorted(p.eav.age for p in Patient.objects.all()) == [0, 1, 2, 3, 4]


def test_bulk_create_covers_every_datatype() -> None:
    doctor = Doctor(name="all")
    doctor.eav.age = 3
    moment = timezone.now().replace(microsecond=0)
    doctor.eav.dob = moment
    doctor.eav.tags = ["a", "b"]
    doctor.eav.extra = {"k": "v"}
    doctor.eav.fever = "yes"

    Doctor.objects.bulk_create([doctor])

    stored = Doctor.objects.get(name="all")
    assert stored.eav.age == 3
    assert stored.eav.tags == ["a", "b"]
    assert stored.eav.extra == {"k": "v"}
    assert stored.eav.fever.value == "yes"
    assert stored.eav.dob == moment


def test_bulk_create_skips_empty_values() -> None:
    doctor = Doctor(name="empty")
    doctor.eav.age = None
    doctor.eav.city = ""

    Doctor.objects.bulk_create([doctor])

    assert Value.objects.count() == 0


def test_bulk_create_without_eav_values_is_plain_bulk_create(
    django_assert_num_queries,
) -> None:
    with django_assert_num_queries(1):
        Doctor.objects.bulk_create([Doctor(name="a"), Doctor(name="b")])


def test_invalid_values_stop_everything_before_any_write() -> None:
    good = Doctor(name="good")
    good.eav.age = 1
    bad = Doctor(name="bad")
    bad.eav.age = "not a number"

    with pytest.raises(ValidationError, match="age EAV field"):
        Doctor.objects.bulk_create([good, bad])

    assert Doctor.objects.count() == 0
    assert Value.objects.count() == 0


def test_required_attributes_are_enforced() -> None:
    Attribute.objects.filter(slug="city").update(required=True)
    doctor = Doctor(name="d")
    doctor.eav.age = 1

    with pytest.raises(ValidationError, match="city EAV field cannot be blank"):
        Doctor.objects.bulk_create([doctor])


def test_unknown_attributes_are_rejected() -> None:
    doctor = Doctor(name="d")
    doctor.eav.age = 1
    doctor.eav.nonsense = 2

    with pytest.raises(IllegalAssignmentException):
        Doctor.objects.bulk_create([doctor])


def test_invalid_enum_choice_is_rejected() -> None:
    doctor = Doctor(name="d")
    doctor.eav.fever = "maybe"

    with pytest.raises(ValidationError, match="not a valid choice"):
        Doctor.objects.bulk_create([doctor])


def test_conflict_options_cannot_be_combined_with_eav_values() -> None:
    doctor = Doctor(name="d")
    doctor.eav.age = 1

    with pytest.raises(NotSupportedError):
        Doctor.objects.bulk_create([doctor], ignore_conflicts=True)


def test_large_input_is_written_in_chunks(django_assert_num_queries) -> None:
    ContentType.objects.get_for_model(Doctor)

    # The savepoint and its release, the attributes, then three chunks of 20, 20
    # and 10 doctors, each with the doctors and two upserts.
    with django_assert_num_queries(2 + 1 + 3 * 3):
        Doctor.objects.bulk_create(_doctors(50), batch_size=20)

    assert Value.objects.count() == 100


def test_bulk_update_writes_eav_fields_and_model_fields(
    django_assert_num_queries,
) -> None:
    doctors = Doctor.objects.bulk_create(_doctors(10))
    for doctor in doctors:
        age = doctor.eav.age
        doctor.name = f"renamed-{age}"
        doctor.eav.age = age + 100
        doctor.eav.city = None

    # The savepoint and its release, the attributes, the model update, the upsert
    # for age and the delete for city.
    with django_assert_num_queries(2 + 1 + 1 + 1 + 1):
        updated = Doctor.objects.bulk_update(doctors, ["name", "eav__age", "eav__city"])

    assert updated == 10
    stored = Doctor.objects.get(name="renamed-3")
    assert stored.eav.age == 103
    assert stored.eav.city is None
    assert Value.objects.filter(attribute__slug="city").count() == 0


def test_bulk_update_only_eav_fields_leaves_other_columns() -> None:
    doctors = Doctor.objects.bulk_create(_doctors(3))
    before = timezone.now()
    for doctor in doctors:
        doctor.eav.age = 99

    Doctor.objects.bulk_update(doctors, ["eav__age"])

    assert {d.eav.age for d in Doctor.objects.all()} == {99}
    assert (
        Value.objects.filter(attribute__slug="age", modified__gte=before).count() == 3
    )


def test_bulk_update_skips_instances_without_an_assigned_value() -> None:
    first, second = Doctor.objects.bulk_create(_doctors(2))
    first.eav.age = 50
    # `second` has no assigned age after reload, so it keeps its stored value.
    second = Doctor.objects.get(pk=second.pk)

    Doctor.objects.bulk_update([first, second], ["eav__age"])

    assert Doctor.objects.get(pk=first.pk).eav.age == 50
    assert Doctor.objects.get(pk=second.pk).eav.age == 1


def test_bulk_update_validates_and_rejects_unknown_attributes() -> None:
    doctor = Doctor.objects.bulk_create(_doctors(1))[0]
    doctor.eav.age = "x"

    with pytest.raises(ValidationError):
        Doctor.objects.bulk_update([doctor], ["eav__age"])

    with pytest.raises(Attribute.DoesNotExist):
        Doctor.objects.bulk_update([doctor], ["eav__missing"])


def test_bulk_update_requires_primary_keys() -> None:
    doctor = Patient(name="unsaved")
    doctor.eav.age = 1

    with pytest.raises(ValueError, match="primary key"):
        Patient.objects.bulk_update([doctor], ["eav__age"])


def test_bulk_update_without_eav_fields_is_plain_bulk_update() -> None:
    doctors = Doctor.objects.bulk_create([Doctor(name="a")])
    doctors[0].name = "b"

    assert Doctor.objects.bulk_update(doctors, ["name"]) == 1
    assert Doctor.objects.get().name == "b"


def test_batch_size_comes_from_the_config(
    monkeypatch: pytest.MonkeyPatch,
    django_assert_num_queries,
) -> None:
    monkeypatch.setattr(Doctor._eav_config_cls, "bulk_batch_size", 10)
    ContentType.objects.get_for_model(Doctor)

    # The savepoint and its release, the attributes, then three chunks of 10, 10
    # and 5 doctors, each with the doctors and two upserts.
    with django_assert_num_queries(2 + 1 + 3 * 3):
        Doctor.objects.bulk_create(_doctors(25))


def test_batch_size_argument_overrides_the_config(
    monkeypatch: pytest.MonkeyPatch,
    django_assert_num_queries,
) -> None:
    monkeypatch.setattr(Doctor._eav_config_cls, "bulk_batch_size", 10)
    ContentType.objects.get_for_model(Doctor)

    # One chunk: the doctors and two upserts, plus the savepoint pair and attributes.
    with django_assert_num_queries(2 + 1 + 3):
        Doctor.objects.bulk_create(_doctors(25), batch_size=100)
