import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

import eav
from eav.models import Attribute, EnumGroup, EnumValue, Value
from test_project.models import Patient


class DataValidation(TestCase):
    def setUp(self):
        eav.register(Patient)

        Attribute.objects.create(name="Age", datatype=Attribute.TYPE_INT)
        Attribute.objects.create(name="DoB", datatype=Attribute.TYPE_DATE)
        Attribute.objects.create(name="Height", datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name="City", datatype=Attribute.TYPE_TEXT)
        Attribute.objects.create(name="Pregnant", datatype=Attribute.TYPE_BOOLEAN)
        Attribute.objects.create(name="User", datatype=Attribute.TYPE_OBJECT)
        Attribute.objects.create(name="Extra", datatype=Attribute.TYPE_JSON)
        Attribute.objects.create(name="Multi", datatype=Attribute.TYPE_CSV)

    def tearDown(self):
        eav.unregister(Patient)

    def test_required_field(self):
        p = Patient(name="Bob")
        p.eav.age = 5
        p.save()

        Attribute.objects.create(
            name="Weight",
            datatype=Attribute.TYPE_INT,
            required=True,
        )
        p.eav.age = 6
        self.assertRaises(ValidationError, p.save)
        p = Patient.objects.get(name="Bob")
        self.assertEqual(p.eav.age, 5)
        p.eav.weight = 23
        p.save()
        p = Patient.objects.get(name="Bob")
        self.assertEqual(p.eav.weight, 23)

    def test_create_required_field(self):
        Attribute.objects.create(
            name="Weight",
            datatype=Attribute.TYPE_INT,
            required=True,
        )
        self.assertRaises(
            ValidationError,
            Patient.objects.create,
            name="Joe",
            eav__age=5,
        )
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Value.objects.count(), 0)

        Patient.objects.create(name="Joe", eav__weight=2, eav__age=5)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 2)

    def test_validation_error_create(self):
        self.assertRaises(
            ValidationError,
            Patient.objects.create,
            name="Joe",
            eav__age="df",
        )
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Value.objects.count(), 0)

    def test_changing_datatypes(self):
        a = Attribute.objects.create(name="Color", datatype=Attribute.TYPE_INT)
        a.datatype = Attribute.TYPE_TEXT
        a.save()
        Patient.objects.create(name="Bob", eav__color="brown")
        a.datatype = Attribute.TYPE_INT
        self.assertRaises(ValidationError, a.save)

    def test_int_validation(self):
        p = Patient.objects.create(name="Joe")
        p.eav.age = "bad"
        self.assertRaises(ValidationError, p.save)
        p.eav.age = 15
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.age, 15)

    def test_date_validation(self):
        p = Patient.objects.create(name="Joe")
        p.eav.dob = "12"
        self.assertRaises(ValidationError, lambda: p.save())
        p.eav.dob = 15
        self.assertRaises(ValidationError, lambda: p.save())
        now = timezone.now()
        p.eav.dob = now
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.dob, now)

    def test_float_validation(self):
        p = Patient.objects.create(name="Joe")
        p.eav.height = "bad"
        self.assertRaises(ValidationError, p.save)
        p.eav.height = 15
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.height, 15)
        p.eav.height = "2.3"
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.height, 2.3)

    def test_text_validation(self):
        p = Patient.objects.create(name="Joe")
        p.eav.city = 5
        self.assertRaises(ValidationError, p.save)
        p.eav.city = "El Dorado"
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.city, "El Dorado")

    def test_bool_validation(self):
        p = Patient.objects.create(name="Joe")
        p.eav.pregnant = 5
        self.assertRaises(ValidationError, p.save)
        p.eav.pregnant = True
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.pregnant, True)

    def test_object_validation(self):
        p = Patient.objects.create(name="Joe")
        p.eav.user = 5
        self.assertRaises(ValidationError, p.save)
        p.eav.user = object
        self.assertRaises(ValidationError, p.save)
        p.eav.user = User(username="joe")
        self.assertRaises(ValidationError, p.save)
        u = User.objects.create(username="joe")
        p.eav.user = u
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.user, u)

    def test_enum_validation(self):
        yes = EnumValue.objects.create(value="yes")
        no = EnumValue.objects.create(value="no")
        unknown = EnumValue.objects.create(value="unknown")
        green = EnumValue.objects.create(value="green")
        ynu = EnumGroup.objects.create(name="Yes / No / Unknown")
        ynu.values.add(yes)
        ynu.values.add(no)
        ynu.values.add(unknown)
        Attribute.objects.create(
            name="Fever",
            datatype=Attribute.TYPE_ENUM,
            enum_group=ynu,
        )

        p = Patient.objects.create(name="Joe")
        p.eav.fever = 5
        self.assertRaises(ValidationError, p.save)
        p.eav.fever = object
        self.assertRaises(ValidationError, p.save)
        p.eav.fever = green
        self.assertRaises(ValidationError, p.save)
        p.eav.fever = EnumValue(value="yes")
        self.assertRaises(ValidationError, p.save)
        p.eav.fever = no
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.fever, no)

    def test_enum_datatype_without_enum_group(self):
        a = Attribute(name="Age Bracket", datatype=Attribute.TYPE_ENUM)
        self.assertRaises(ValidationError, a.save)
        yes = EnumValue.objects.create(value="yes")
        no = EnumValue.objects.create(value="no")
        unknown = EnumValue.objects.create(value="unknown")
        ynu = EnumGroup.objects.create(name="Yes / No / Unknown")
        ynu.values.add(yes)
        ynu.values.add(no)
        ynu.values.add(unknown)
        a = Attribute(name="Age Bracket", datatype=Attribute.TYPE_ENUM, enum_group=ynu)
        a.save()

    def test_enum_group_on_other_datatype(self):
        yes = EnumValue.objects.create(value="yes")
        no = EnumValue.objects.create(value="no")
        unknown = EnumValue.objects.create(value="unknown")
        ynu = EnumGroup.objects.create(name="Yes / No / Unknown")
        ynu.values.add(yes)
        ynu.values.add(no)
        ynu.values.add(unknown)
        a = Attribute(name="color", datatype=Attribute.TYPE_TEXT, enum_group=ynu)
        self.assertRaises(ValidationError, a.save)

    def test_json_validation(self):
        p = Patient.objects.create(name="Joe")
        p.eav.extra = 5
        self.assertRaises(ValidationError, p.save)
        p.eav.extra = {"eyes": "blue", "hair": "brown"}
        p.save()
        self.assertEqual(Patient.objects.get(pk=p.pk).eav.extra.get("eyes", ""), "blue")

    def test_csv_validation(self):
        yes = EnumValue.objects.create(value="yes")
        p = Patient.objects.create(name="Mike")
        p.eav.multi = yes
        self.assertRaises(ValidationError, p.save)
        p.eav.multi = "one;two;three"
        p.save()
        self.assertEqual(
            Patient.objects.get(pk=p.pk).eav.multi,
            ["one", "two", "three"],
        )


@pytest.mark.django_db
def test_date_value_is_stored_as_midnight_in_the_default_timezone():
    eav.register(Patient)
    Attribute.objects.create(name="DoB", datatype=Attribute.TYPE_DATE)
    today = timezone.now().date()
    patient = Patient.objects.create(name="Joe")
    patient.eav.dob = today
    patient.save()

    stored = Patient.objects.get(pk=patient.pk).eav.dob

    assert stored.date() == today
    assert stored.time() == dt.time.min
    assert timezone.is_aware(stored)


@pytest.mark.django_db
def test_saving_the_same_date_again_writes_nothing(django_assert_num_queries):
    eav.register(Patient)
    Attribute.objects.create(name="DoB", datatype=Attribute.TYPE_DATE)
    today = timezone.now().date()
    patient = Patient.objects.create(name="Joe", eav__dob=today)
    patient = Patient.objects.get(pk=patient.pk)
    patient.eav.dob = today

    # The update, the attributes and the values; no write for the date.
    with django_assert_num_queries(3):
        patient.save()
