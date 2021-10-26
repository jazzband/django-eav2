import pytest
from django.test import TestCase

import eav
from eav.models import Attribute, EnumGroup, EnumValue, Value
from test_project.models import Patient


@pytest.fixture()
def enumgroup(db):
    """Sample `EnumGroup` object for testing."""
    test_group = EnumGroup.objects.create(name='Yes / No')
    value_yes = EnumValue.objects.create(value='Yes')
    value_no = EnumValue.objects.create(value='No')
    test_group.values.add(value_yes)
    test_group.values.add(value_no)
    return test_group


def test_enumgroup_display(enumgroup):
    """Test repr() and str() of EnumGroup."""
    assert '<EnumGroup {0}>'.format(enumgroup.name) == repr(enumgroup)
    assert str(enumgroup) == str(enumgroup.name)


def test_enumvalue_display(enumgroup):
    """Test repr() and str() of EnumValue."""
    test_value = enumgroup.values.first()
    assert '<EnumValue {0}>'.format(test_value.value) == repr(test_value)
    assert str(test_value) == test_value.value


class MiscModels(TestCase):
    """Miscellaneous tests on models."""

    def test_attribute_help_text(self):
        desc = 'Patient Age'
        a = Attribute.objects.create(
            name='age', description=desc, datatype=Attribute.TYPE_INT
        )
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
        Attribute.objects.create(
            name='is_patient', datatype=Attribute.TYPE_ENUM, enum_group=ynu
        )
        eav.register(Patient)
        p = Patient.objects.create(name='Joe')
        p.eav.is_patient = 'yes'
        p.save()
        p = Patient.objects.get(name='Joe')  # get from DB again
        self.assertEqual(p.eav.is_patient, yes)
