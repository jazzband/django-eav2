import eav
import datetime
from django.test import TestCase
from eav.models import EnumValue, EnumGroup, Attribute, Value
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


class EnumValueTestCase(TestCase):
    def setUp(self):
        self.enum_value = EnumValue.objects.create(value='Test Value')

    def test_enum_value_str(self):
        self.assertEqual(str(self.enum_value), 'Test Value')


class EnumGroupTestCase(TestCase):
    def setUp(self):
        self.enum_group = EnumGroup.objects.create(name='Test Group')

    def test_enum_group_str(self):
        self.assertEqual(str(self.enum_group), 'Test Group')


class AttributeTestCase(TestCase):
    def setUp(self):
        self.attribute = Attribute.objects.create(
            name='Test Attribute', datatype='text'
        )

    def test_attribute_str(self):
        self.assertEqual(str(self.attribute), 'Test Attribute (Text)')


class ValueModelTestCase(TestCase):
    def setUp(self):
        eav.register(User)
        self.attribute = Attribute.objects.create(
            name='Test Attribute', datatype=Attribute.TYPE_TEXT, slug="test_attribute"
        )
        self.user = User.objects.create(username='crazy_dev_user')
        user_content_type = ContentType.objects.get_for_model(User)
        self.value = Value.objects.create(
            entity_id=self.user.id,
            entity_ct=user_content_type,
            value_text='Test Value',
            attribute=self.attribute,
        )

    def test_value_str(self):
        expected_str = f'{self.attribute.name}: "{self.value.value_text}" ({self.value.entity_pk_int})'
        self.assertEqual(str(self.value), expected_str)
