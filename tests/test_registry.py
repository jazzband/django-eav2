from django.contrib.auth.models import User
from django.test import TestCase

import eav
from eav.registry import EavConfig
from test_project.models import (
    Encounter,
    ExampleMetaclassModel,
    ExampleModel,
    Patient,
)


class RegistryTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def register_encounter(self):
        class EncounterEav(EavConfig):
            manager_attr = 'eav_objects'
            eav_attr = 'eav_field'
            generic_relation_attr = 'encounter_eav_values'
            generic_relation_related_name = 'encounters'

            @classmethod
            def get_attributes(cls):
                return 'testing'

        eav.register(Encounter, EncounterEav)

    def test_registering_with_defaults(self):
        eav.register(Patient)
        self.assertTrue(hasattr(Patient, '_eav_config_cls'))
        self.assertEqual(Patient._eav_config_cls.manager_attr, 'objects')
        self.assertFalse(Patient._eav_config_cls.manager_only)
        self.assertEqual(Patient._eav_config_cls.eav_attr, 'eav')
        self.assertEqual(Patient._eav_config_cls.generic_relation_attr, 'eav_values')
        self.assertEqual(Patient._eav_config_cls.generic_relation_related_name, None)
        eav.unregister(Patient)

    def test_registering_overriding_defaults(self):
        eav.register(Patient)
        self.register_encounter()
        self.assertTrue(hasattr(Patient, '_eav_config_cls'))
        self.assertEqual(Patient._eav_config_cls.manager_attr, 'objects')
        self.assertEqual(Patient._eav_config_cls.eav_attr, 'eav')

        self.assertTrue(hasattr(Encounter, '_eav_config_cls'))
        self.assertEqual(Encounter._eav_config_cls.get_attributes(), 'testing')
        self.assertEqual(Encounter._eav_config_cls.manager_attr, 'eav_objects')
        self.assertEqual(Encounter._eav_config_cls.eav_attr, 'eav_field')
        eav.unregister(Patient)
        eav.unregister(Encounter)

    def test_registering_via_decorator_with_defaults(self):
        self.assertTrue(hasattr(ExampleModel, '_eav_config_cls'))
        self.assertEqual(ExampleModel._eav_config_cls.manager_attr, 'objects')
        self.assertEqual(ExampleModel._eav_config_cls.eav_attr, 'eav')

    def test_register_via_metaclass_with_defaults(self):
        self.assertTrue(hasattr(ExampleMetaclassModel, '_eav_config_cls'))
        self.assertEqual(ExampleMetaclassModel._eav_config_cls.manager_attr, 'objects')
        self.assertEqual(ExampleMetaclassModel._eav_config_cls.eav_attr, 'eav')

    def test_unregistering(self):
        old_mgr = Patient.objects
        eav.register(Patient)
        self.assertTrue(Patient.objects.__class__.__name__ == 'EntityManager')
        eav.unregister(Patient)
        self.assertFalse(Patient.objects.__class__.__name__ == 'EntityManager')
        self.assertEqual(Patient.objects, old_mgr)
        self.assertFalse(hasattr(Patient, '_eav_config_cls'))

    def test_unregistering_via_decorator(self):
        self.assertTrue(ExampleModel.objects.__class__.__name__ == 'EntityManager')
        eav.unregister(ExampleModel)
        self.assertFalse(ExampleModel.objects.__class__.__name__ == 'EntityManager')

    def test_unregistering_via_metaclass(self):
        self.assertTrue(
            ExampleMetaclassModel.objects.__class__.__name__ == 'EntityManager'
        )
        eav.unregister(ExampleMetaclassModel)
        self.assertFalse(
            ExampleMetaclassModel.objects.__class__.__name__ == 'EntityManager'
        )

    def test_unregistering_unregistered_model_proceeds_silently(self):
        eav.unregister(Patient)

    def test_double_registering_model_is_harmless(self):
        eav.register(Patient)
        eav.register(Patient)

    def test_doesnt_register_nonmodel(self):
        with self.assertRaises(ValueError):

            @eav.decorators.register_eav()
            class Foo(object):
                pass

    def test_model_without_local_managers(self):
        """Test when a model doesn't have local_managers."""
        # Check just in case test model changes in the future
        assert bool(User._meta.local_managers) is False
        eav.register(User)
        assert isinstance(User.objects, eav.managers.EntityManager)

        # Reverse check: managers should be empty again
        eav.unregister(User)
        assert bool(User._meta.local_managers) is False
