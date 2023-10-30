from django.test import TestCase
from eav.models import Attribute, EnumGroup, EnumValue, Value
from test_project.models import Patient
import eav


class ModelTest(TestCase):
    def setUp(self):
        eav.register(Patient)
        Attribute.objects.create(name='age', datatype=Attribute.TYPE_INT)
        Attribute.objects.create(name='height', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='weight', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='color', datatype=Attribute.TYPE_TEXT)

        EnumGroup.objects.create(name='Yes / No')
        EnumValue.objects.create(value='yes')
        EnumValue.objects.create(value='no')
        EnumValue.objects.create(value='unknown')

    def test_attr_natural_keys(self):
        attr = Attribute.objects.get(name='age')
        attr_natural_key = attr.natural_key()
        attr_retrieved_model = Attribute.objects.get_by_natural_key(*attr_natural_key)
        self.assertEqual(attr_retrieved_model, attr)

    def test_value_natural_keys(self):
        p = Patient.objects.create(name='Jon')
        p.eav.age = 5
        p.save()

        val = p.eav_values.first()

        value_natural_key = val.natural_key()
        value_retrieved_model = Value.objects.get_by_natural_key(*value_natural_key)
        self.assertEqual(value_retrieved_model, val)

    def test_enum_group_natural_keys(self):
        enum_group = EnumGroup.objects.first()
        enum_group_natural_key = enum_group.natural_key()
        enum_group_retrieved_model = EnumGroup.objects.get_by_natural_key(
            *enum_group_natural_key
        )
        self.assertEqual(enum_group_retrieved_model, enum_group)

    def test_enum_value_natural_keys(self):
        enum_value = EnumValue.objects.first()
        enum_value_natural_key = enum_value.natural_key()
        enum_value_retrieved_model = EnumValue.objects.get_by_natural_key(
            *enum_value_natural_key
        )
        self.assertEqual(enum_value_retrieved_model, enum_value)
