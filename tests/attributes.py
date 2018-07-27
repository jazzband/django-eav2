from django.core.exceptions import ValidationError
from django.test import TestCase

import sys
import eav
from eav.exceptions import IllegalAssignmentException
from eav.models import Attribute, Value
from eav.registry import EavConfig

from .models import Encounter, Patient

if sys.version_info[0] > 2:
    from .metaclass_models3 import RegisterTestModel
else:
    from .metaclass_models2 import RegisterTestModel

class Attributes(TestCase):
    def setUp(self):
        class EncounterEavConfig(EavConfig):
            manager_attr = 'eav_objects'
            eav_attr = 'eav_field'
            generic_relation_attr = 'encounter_eav_values'
            generic_relation_related_name = 'encounters'

            @classmethod
            def get_attributes(cls):
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

    def test_illegal_assignemnt(self):
        class EncounterEavConfig(EavConfig):
            @classmethod
            def get_attributes(cls):
                return Attribute.objects.filter(datatype=Attribute.TYPE_INT)

        eav.unregister(Encounter)
        eav.register(Encounter, EncounterEavConfig)

        p = Patient.objects.create(name='Jon')
        e = Encounter.objects.create(patient=p, num=1)

        with self.assertRaises(IllegalAssignmentException):
            e.eav.color = 'red'
            e.save()
