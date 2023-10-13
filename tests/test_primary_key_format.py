# test_primary_key_format.py

from django.test import TestCase
from django.conf import settings
from django.db import models
from functools import partial
import uuid
from eav.logic.object_pk import get_pk_format


class GetPrimaryKeyFormatTestCase(TestCase):
    def test_get_uuid_primary_key(self):
        settings.PRIMARY_KEY_FIELD = "django.db.models.UUIDField"
        primary_field = get_pk_format()
        self.assertTrue(isinstance(primary_field, models.UUIDField))
        self.assertTrue(primary_field.primary_key)
        self.assertFalse(primary_field.editable)
        self.assertEqual(primary_field.default, uuid.uuid4)

    def test_get_char_primary_key(self):
        settings.PRIMARY_KEY_FIELD = "django.db.models.CharField"
        primary_field = get_pk_format()
        self.assertTrue(isinstance(primary_field, models.CharField))
        self.assertTrue(primary_field.primary_key)
        self.assertFalse(primary_field.editable)
        self.assertEqual(primary_field.max_length, 40)

    def test_get_default_primary_key(self):
        # This test covers the default case for "BigAutoField"
        settings.PRIMARY_KEY_FIELD = "AnyOtherField"
        primary_field = get_pk_format()
        self.assertTrue(isinstance(primary_field, models.BigAutoField))
        self.assertTrue(primary_field.primary_key)
        self.assertFalse(primary_field.editable)

    def test_unrecognized_primary_key_field(self):
        # Test when an unrecognized primary key field is specified in settings
        settings.PRIMARY_KEY_FIELD = "UnrecognizedField"
        with self.assertRaises(ValueError):
            get_pk_format()

    def tearDown(self):
        # Reset the PRIMARY_KEY_FIELD setting after each test
        settings.PRIMARY_KEY_FIELD = "django.db.models.BigAutoField"
