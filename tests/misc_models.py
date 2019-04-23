from django.test import TestCase

from eav.models import EnumGroup, Attribute, Value, EnumValue

import eav
from .models import Patient


class MiscModels(TestCase):
    def test_enumgroup_str(self):
        name = 'Yes / No'
        e = EnumGroup.objects.create(name=name)
        self.assertEqual('<EnumGroup Yes / No>', str(e))

    def test_attribute_help_text(self):
        desc = 'Patient Age'
        a = Attribute.objects.create(name='age', description=desc, datatype=Attribute.TYPE_INT)
        self.assertEqual(a.help_text, desc)

    def test_setting_to_none_deletes_value(self):
        eav.register(Patient)
        Attribute.objects.create(name='age', datatype=Attribute.TYPE_INT)
        p = Patient.objects.create(name='Bob', eav__age=5)
        self.assertEqual(Value.objects.count(), 1)
        p.eav.age = None
        p.save()
        self.assertEqual(Value.objects.count(), 0)

    def test_string_enum_value_assignment(self):
        yes = EnumValue.objects.create(value='yes')
        no = EnumValue.objects.create(value='no')
        ynu = EnumGroup.objects.create(name='Yes / No / Unknown')
        ynu.values.add(yes)
        ynu.values.add(no)
        Attribute.objects.create(name='is_patient', datatype=Attribute.TYPE_ENUM, enum_group=ynu)
        eav.register(Patient)
        p = Patient.objects.create(name='Joe')
        p.eav.is_patient = 'yes'
        p.save()
        p = Patient.objects.get(name='Joe')  # get from DB again
        self.assertEqual(p.eav.is_patient, yes)
