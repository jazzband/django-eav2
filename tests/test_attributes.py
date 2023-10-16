import uuid
import string

from django.core.exceptions import ValidationError
from django.test import TestCase
from hypothesis import given, settings
from hypothesis.extra import django
from django.conf import settings as django_settings
from hypothesis import strategies as st
from hypothesis.strategies import just

import eav
from eav.exceptions import IllegalAssignmentException
from eav.models import Attribute, Value
from eav.registry import EavConfig
from test_project.models import Doctor, Encounter, Patient, RegisterTestModel


if django_settings.EAV2_PRIMARY_KEY_FIELD == "django.db.models.UUIDField":
    auto_field_strategy = st.builds(uuid.uuid4, version=4, max_length=32)
elif django_settings.EAV2_PRIMARY_KEY_FIELD == "django.db.models.CharField":
    auto_field_strategy = st.text(min_size=1, max_size=255)
else:
    auto_field_strategy = st.integers(min_value=1, max_value=32)


class Attributes(TestCase):
    def setUp(self):
        class EncounterEavConfig(EavConfig):
            manager_attr = 'eav_objects'
            eav_attr = 'eav_field'
            generic_relation_attr = 'encounter_eav_values'
            generic_relation_related_name = 'encounters'

            @classmethod
            def get_attributes(cls, instance=None):
                return Attribute.objects.filter(slug__contains='a')

        eav.register(Encounter, EncounterEavConfig)
        eav.register(Patient)

        Attribute.objects.create(name='age', datatype=Attribute.TYPE_INT)
        Attribute.objects.create(name='height', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='weight', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='color', datatype=Attribute.TYPE_TEXT)

    def tearDown(self):
        eav.unregister(Encounter)
        eav.unregister(Patient)

    def test_get_attribute_querysets(self):
        self.assertEqual(Patient._eav_config_cls.get_attributes().count(), 4)
        self.assertEqual(Encounter._eav_config_cls.get_attributes().count(), 1)

    def test_duplicate_attributs(self):
        '''
        Ensure that no two Attributes with the same slug can exist.
        '''
        with self.assertRaises(ValidationError):
            Attribute.objects.create(name='height', datatype=Attribute.TYPE_FLOAT)

    def test_setting_attributes(self):
        p = Patient.objects.create(name='Jon')
        e = Encounter.objects.create(patient=p, num=1)

        p.eav.age = 3
        p.eav.height = 2.3
        p.save()
        e.eav_field.age = 4
        e.save()
        self.assertEqual(Value.objects.count(), 3)
        t = RegisterTestModel.objects.create(name="test")
        t.eav.age = 6
        t.eav.height = 10
        t.save()
        p = Patient.objects.get(name='Jon')
        self.assertEqual(p.eav.age, 3)
        self.assertEqual(p.eav.height, 2.3)
        e = Encounter.objects.get(num=1)
        self.assertEqual(e.eav_field.age, 4)
        t = RegisterTestModel.objects.get(name="test")
        self.assertEqual(t.eav.age, 6)
        self.assertEqual(t.eav.height, 10)

        # Validate repr of Value for an entity with an INT PK
        v1 = Value.objects.filter(entity_id=p.pk).first()
        assert isinstance(repr(v1), str)
        assert isinstance(str(v1), str)

    def test_illegal_assignemnt(self):
        class EncounterEavConfig(EavConfig):
            @classmethod
            def get_attributes(cls, instance=None):
                return Attribute.objects.filter(datatype=Attribute.TYPE_INT)

        eav.unregister(Encounter)
        eav.register(Encounter, EncounterEavConfig)

        p = Patient.objects.create(name='Jon')
        e = Encounter.objects.create(patient=p, num=1)

        with self.assertRaises(IllegalAssignmentException):
            e.eav.color = 'red'
            e.save()

    def test_uuid_pk(self):
        """Tests for when model pk is UUID."""
        d1 = Doctor.objects.create(name='Lu')
        d1.eav.age = 10
        d1.save()

        assert d1.eav.age == 10

        # Validate repr of Value for an entity with a UUID PK
        v1 = Value.objects.filter(entity_uuid=d1.pk).first()
        assert isinstance(repr(v1), str)
        assert isinstance(str(v1), str)

    def test_big_integer(self):
        """Tests an integer larger than 32-bit a value."""
        big_num = 3147483647
        patient = Patient.objects.create(name='Jon')
        patient.eav.age = big_num

        patient.save()

        assert patient.eav.age == big_num


class TestAttributeModel(django.TestCase):
    """This is a property-based test that ensures model correctness."""

    @given(
        django.from_model(
            Attribute,
            id=auto_field_strategy,
            datatype=just(Attribute.TYPE_TEXT),
            enum_group=just(None),
        ),
    )
    @settings(deadline=None)
    def test_model_properties(self, attribute: Attribute) -> None:
        """Tests that instance can be saved and has correct representation."""
        attribute.full_clean()
        attribute.save()

        assert attribute

    @given(
        st.text(
            alphabet=st.sampled_from(string.ascii_letters + string.digits),
            min_size=50,
            max_size=100,
        ),
    )
    def test_large_name_input(self, name_value) -> None:
        """Ensure proper slug is generated from large name fields."""
        instance = Attribute.objects.create(
            name=name_value,
            datatype=Attribute.TYPE_TEXT,
            enum_group=None,
        )

        assert isinstance(instance, Attribute)
