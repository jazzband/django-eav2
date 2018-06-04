from django.test import TestCase

import eav
from eav.registry import EavConfig

from .models import Patient, Encounter


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
        eav.register(Encounter, EncounterEav)


    def test_registering_with_defaults(self):
        eav.register(Patient)
        self.assertTrue(hasattr(Patient, '_eav_config_cls'))
        self.assertEqual(Patient._eav_config_cls.manager_attr, 'objects')
        self.assertFalse(Patient._eav_config_cls.manager_only)
        self.assertEqual(Patient._eav_config_cls.eav_attr, 'eav')
        self.assertEqual(Patient._eav_config_cls.generic_relation_attr,
                         'eav_values')
        self.assertEqual(Patient._eav_config_cls.generic_relation_related_name,
                         None)
        eav.unregister(Patient)

    def test_registering_overriding_defaults(self):
        eav.register(Patient)
        self.register_encounter()
        self.assertTrue(hasattr(Patient, '_eav_config_cls'))
        self.assertEqual(Patient._eav_config_cls.manager_attr, 'objects')
        self.assertEqual(Patient._eav_config_cls.eav_attr, 'eav')

        self.assertTrue(hasattr(Encounter, '_eav_config_cls'))
        self.assertEqual(Encounter._eav_config_cls.manager_attr, 'eav_objects')
        self.assertEqual(Encounter._eav_config_cls.eav_attr, 'eav_field')
        eav.unregister(Patient)
        eav.unregister(Encounter)

    def test_unregistering(self):
        old_mgr = Patient.objects
        eav.register(Patient)
        self.assertTrue(Patient.objects.__class__.__name__ == 'EntityManager')
        eav.unregister(Patient)
        self.assertFalse(Patient.objects.__class__.__name__ == 'EntityManager')
        self.assertEqual(Patient.objects, old_mgr)
        self.assertFalse(hasattr(Patient, '_eav_config_cls'))

    def test_unregistering_unregistered_model_proceeds_silently(self):
        eav.unregister(Patient)

    def test_double_registering_model_is_harmless(self):
        eav.register(Patient)
        eav.register(Patient)
