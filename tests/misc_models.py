from django.test import TestCase

from eav.models import EnumGroup, Attribute, Value

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
