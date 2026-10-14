"""Lock in how many queries the entity helpers run."""

from __future__ import annotations

import pickle

import pytest
from django.contrib.contenttypes.models import ContentType

import eav
from eav.models import Attribute, EnumGroup, EnumValue, Value
from eav.registry import EavConfig
from test_project.models import Patient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _schema() -> None:
    eav.register(Patient)
    Attribute.objects.create(name="age", datatype=Attribute.TYPE_INT)
    Attribute.objects.create(name="height", datatype=Attribute.TYPE_FLOAT)
    Attribute.objects.create(name="city", datatype=Attribute.TYPE_TEXT)
    Attribute.objects.create(name="weight", datatype=Attribute.TYPE_INT)
    # Looked up once per process, so warm it to keep the counts stable:
    ContentType.objects.get_for_model(Patient)


@pytest.fixture
def patient() -> Patient:
    patient = Patient.objects.create(name="Joe", eav__age=3, eav__city="Rome")
    return Patient.objects.get(pk=patient.pk)


def test_create_with_attributes_loads_the_schema_once(
    django_assert_num_queries,
) -> None:
    # The patient, the attributes, and one insert per value.
    with django_assert_num_queries(1 + 1 + 3):
        Patient.objects.create(name="Ann", eav__age=1, eav__height=1.5, eav__city="X")


def test_first_read_loads_attributes_and_values(
    patient: Patient,
    django_assert_num_queries,
) -> None:
    with django_assert_num_queries(2):
        assert patient.eav.age == 3


def test_later_reads_are_free(patient: Patient, django_assert_num_queries) -> None:
    assert patient.eav.age == 3

    with django_assert_num_queries(0):
        assert patient.eav.city == "Rome"
        assert patient.eav.age == 3
        assert patient.eav.weight is None


def test_save_without_changes(patient: Patient, django_assert_num_queries) -> None:
    # The update, then the attributes and values to validate against.
    with django_assert_num_queries(3):
        patient.save()


def test_save_with_one_changed_value(
    patient: Patient,
    django_assert_num_queries,
) -> None:
    patient.eav.age = 4

    with django_assert_num_queries(3 + 1):
        patient.save()

    assert Patient.objects.get(pk=patient.pk).eav.age == 4


def test_save_with_an_unchanged_value_writes_nothing(
    patient: Patient,
    django_assert_num_queries,
) -> None:
    patient.eav.age = 3

    with django_assert_num_queries(3):
        patient.save()


def test_clearing_a_value_deletes_it(patient: Patient) -> None:
    patient.eav.city = None
    patient.save()

    assert Patient.objects.get(pk=patient.pk).eav.city is None
    assert not Value.objects.filter(value_text="Rome").exists()


def test_saving_an_enum_value(patient: Patient, django_assert_num_queries) -> None:
    yes = EnumValue.objects.create(value="yes")
    group = EnumGroup.objects.create(name="yes no")
    group.values.add(yes)
    Attribute.objects.create(
        name="fever",
        datatype=Attribute.TYPE_ENUM,
        enum_group=group,
    )
    patient.eav.fever = "yes"

    # The update, attributes, values, the enum lookup and check, and the insert.
    with django_assert_num_queries(6):
        patient.save()

    assert Patient.objects.get(pk=patient.pk).eav.fever == yes


def test_prefetch_loads_a_list_in_constant_queries(django_assert_num_queries) -> None:
    for number in range(10):
        Patient.objects.create(name=f"p{number}", eav__age=number)

    queryset = Patient.objects.order_by("name").prefetch_related(
        "eav_values__attribute",
    )

    # The patients, their values, and the values' attributes.
    with django_assert_num_queries(3):
        ages = {patient.name: patient.eav.age for patient in queryset}

    assert ages == {f"p{number}": number for number in range(10)}


def test_refresh_from_db_clears_the_cache(patient: Patient) -> None:
    assert patient.eav.age == 3
    Value.objects.filter(attribute__slug="age").update(value_int=9)

    assert patient.eav.age == 3
    patient.refresh_from_db()

    assert patient.eav.age == 9


def test_clear_cache_rereads_values(patient: Patient) -> None:
    assert patient.eav.age == 3
    Value.objects.filter(attribute__slug="age").update(value_int=9)

    patient.eav.clear_cache()

    assert patient.eav.age == 9


def test_attribute_created_after_the_schema_was_cached_is_found(
    patient: Patient,
) -> None:
    assert patient.eav.age == 3
    Attribute.objects.create(name="shoe", datatype=Attribute.TYPE_INT)

    assert patient.eav.shoe is None


def test_unknown_attribute_still_raises(patient: Patient) -> None:
    with pytest.raises(AttributeError, match="no EAV attribute named nope"):
        patient.eav.nope  # noqa: B018


def test_instances_from_a_list_can_be_pickled() -> None:
    Patient.objects.create(name="a", eav__age=1)
    Patient.objects.create(name="b", eav__age=2)
    first, _second = Patient.objects.order_by("name")
    assert first.eav.age == 1

    restored = pickle.loads(pickle.dumps(first))  # noqa: S301

    assert restored.eav.age == 1


def test_public_entity_helpers(patient: Patient) -> None:
    age = Attribute.objects.get(slug="age")
    weight = Attribute.objects.get(slug="weight")

    assert patient.eav.get_all_attribute_slugs() == {"age", "height", "city", "weight"}
    assert patient.eav.get_attribute_by_slug("age") == age
    assert patient.eav.get_value_by_attribute(age).value == 3
    assert patient.eav.get_values_dict() == {"age": 3, "city": "Rome"}
    assert {eav_value.attribute.slug for eav_value in patient.eav} == {"age", "city"}
    assert patient.eav.get_values().count() == 2

    with pytest.raises(Value.DoesNotExist):
        patient.eav.get_value_by_attribute(weight)

    with pytest.raises(Attribute.DoesNotExist):
        patient.eav.get_attribute_by_slug("nope")


def test_attribute_save_value_still_stores_and_deletes(patient: Patient) -> None:
    weight = Attribute.objects.get(slug="weight")

    stored = weight.save_value(patient, 70)
    assert stored is not None
    assert Patient.objects.get(pk=patient.pk).eav.weight == 70

    assert weight.save_value(patient, None) is None
    assert Patient.objects.get(pk=patient.pk).eav.weight is None


def test_the_next_read_after_a_save_reloads_the_values(
    patient: Patient,
    django_assert_num_queries,
) -> None:
    patient.eav.age = 4
    patient.save()

    # Saving evicts the values; the attributes stay loaded.
    with django_assert_num_queries(1):
        assert patient.eav.city == "Rome"


def test_list_shares_one_attribute_lookup(django_assert_num_queries) -> None:
    for number in range(10):
        Patient.objects.create(name=f"p{number}", eav__age=number)

    # The patients, one lookup of the attributes, then each patient's values.
    with django_assert_num_queries(1 + 1 + 10):
        ages = [patient.eav.age for patient in Patient.objects.all()]

    assert sorted(a for a in ages if a is not None) == list(range(10))


def test_iterator_shares_one_attribute_lookup(django_assert_num_queries) -> None:
    for number in range(5):
        Patient.objects.create(name=f"p{number}", eav__age=number)

    with django_assert_num_queries(1 + 1 + 5):
        assert len([patient.eav.age for patient in Patient.objects.iterator()]) == 5


def test_values_querysets_are_unaffected() -> None:
    Patient.objects.create(name="a", eav__age=1)

    assert list(Patient.objects.values("name")) == [{"name": "a"}]
    assert list(Patient.objects.values_list("name", flat=True)) == ["a"]


def test_config_shares_attributes_unless_get_attributes_is_overridden() -> None:
    class Overriding(EavConfig):
        @classmethod
        def get_attributes(cls, instance=None):
            return Attribute.objects.none()

    class Inheriting(EavConfig):
        manager_attr = "objects"

    class InheritingOverride(Overriding):
        pass

    assert EavConfig.shares_attributes()
    assert Inheriting.shares_attributes()
    assert not Overriding.shares_attributes()
    assert not InheritingOverride.shares_attributes()


def test_entities_of_a_custom_config_do_not_share_attributes() -> None:
    class Scoped(EavConfig):
        @classmethod
        def get_attributes(cls, instance=None):
            return Attribute.objects.filter(slug="age")

    eav.unregister(Patient)
    eav.register(Patient, Scoped)
    for name in ("a", "b"):
        Patient.objects.create(name=name, eav__age=1)

    first, second = Patient.objects.order_by("name")

    assert first.eav.age == second.eav.age == 1
    assert first.eav._schema is not second.eav._schema
