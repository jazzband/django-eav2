from datetime import datetime

from django.test import TestCase

from ..models import *
from ..utils import EavRegistry, EavConfig
from .models import Patient


class EavBasicTests(TestCase):

    """
        Testing basics such as registration, printing and object creation
    """


    def setUp(self):
    
        EavRegistry.unregister(Patient)
        EavRegistry.register(Patient)

        self.attribute = Attribute.objects.create(datatype=Attribute.TYPE_TEXT,
                                                name='City', help_text='The City', slug='city')
                                                
        self.entity = Patient.objects.create(name="Doe")

        self.value = Value.objects.create(entity=self.entity,
                                             attribute=self.attribute,
                                             value_text='Denver')

    def tearDown(self):
        EavRegistry.unregister(Patient)


    def test_attribute_unicode(self):
        self.assertEqual(unicode(self.attribute), "City (Text)")


    def test_can_create_attribute(self):
        Attribute.objects.create(datatype=Attribute.TYPE_TEXT,
                                    name='My text test', slug='test',
                                    help_text='My help text')


    def test_can_eaventity_children_give_you_all_attributes_by_default(self):
        qs = Patient.eav.get_eav_attributes()
        self.assertEqual(list(qs), list(Attribute.objects.all()))


    def test_value_creation(self):
        Value.objects.create(entity=self.entity,
                                attribute=self.attribute,
                                value_float=1.2)

    def test_value_unicode(self):
        self.assertEqual(unicode(self.value), "Doe - City: \"Denver\"")



    def test_value_types(self):
        _text = Attribute.objects.create(datatype=Attribute.TYPE_TEXT,
                                            name='Text', slug='text',
                                            help_text='The text')
        val = Value.objects.create(entity=self.entity,
                                       attribute = _text)
        value = "Test text"
        val.value = value
        val.save()
        self.assertEqual(val.value, value)              

        _float = Attribute.objects.create(datatype=Attribute.TYPE_FLOAT,
                                             name='Float', slug='float',
                                             help_text='The float')
        val = Value.objects.create(entity=self.entity,
                                       attribute = _float)
        value = 1.22
        val.value = value
        val.save()
        self.assertEqual(val.value, value)


        _int = Attribute.objects.create(datatype=Attribute.TYPE_INT,
                                           name='Int', slug='int',
                                           help_text='The int')
        val = Value.objects.create(entity=self.entity,
                                       attribute = _int)
        value = 7
        val.value = value
        val.save()
        self.assertEqual(val.value, value)

        _date = Attribute.objects.create(datatype=Attribute.TYPE_DATE,
                                            name='Date', slug='date',
                                            help_text='The date')
        val = Value.objects.create(entity=self.entity,
                                       attribute = _date)
        value = datetime.now()
        val.value = value
        val.save()
        self.assertEqual(val.value, value)

        _bool = Attribute.objects.create(datatype=Attribute.TYPE_BOOLEAN,
                                            name='Bool', slug='bool',
                                            help_text='The bool')
        val = Value.objects.create(entity=self.entity,
                                       attribute = _bool)
        value = False
        val.value = value
        val.save()
        self.assertEqual(val.value, value)
        

    def test_eavregistry_ataches_and_detaches_eav_attribute(self):
        EavRegistry.unregister(Patient)
        p = Patient()
        self.assertFalse(hasattr(p, 'eav'))

        EavRegistry.register(Patient)
        p2 = Patient()
        self.assertTrue(p2.eav)


    def test_eavregistry_ataches_and_detaches_eav_attribute(self):
        
        self.assertTrue(self.entity.eav)
        self.assertTrue(self.entity.eav_values)
        self.assertTrue(self.value.entity)
        # todo : should we have self.value.patient herer ?
       
        EavRegistry.unregister(Patient)
        p = Patient()
        self.assertFalse(hasattr(p, 'eav'))
        self.assertFalse(hasattr(p, 'eav'))
        self.assertFalse(hasattr(p, 'eav_values'))
        

    def test_eavregistry_accept_a_settings_class_with_get_queryset(self):
        EavRegistry.unregister(Patient)

        class PatientEav(EavConfig):

            @classmethod
            def get_eav_attributes(self):
                return Attribute.objects.all()

        EavRegistry.register(Patient, PatientEav)
        
        p = Patient()

        EavRegistry.unregister(Patient)
        
    
    def test_eavregistry_accept_a_settings_class_with_field_names(self):
        
        p = Patient.objects.create(name='Renaud')
        registered_manager = Patient.objects   
        registered_eav_value = p.eav_values
        EavRegistry.unregister(Patient)

        class PatientEav(EavConfig):

            eav_attr = 'my_eav'
            manager_attr ='my_objects'
            generic_relation_attr  = 'my_eav_values'
            generic_relation_related_name = "patient"

        EavRegistry.register(Patient, PatientEav)
        
        p2 = Patient.objects.create(name='Henry')
        self.assertEqual(type(p.eav), type(p2.my_eav))
        self.assertEqual(registered_eav_value.__class__.__name__, 
                         p2.my_eav_values.__class__.__name__ )
        self.assertEqual(type(registered_manager), type(Patient.my_objects))
                         
        p2.my_eav.city = "Mbrarare"
        p2.save()
        value = Value.objects.get(value_text='Mbrarare')
        name = PatientEav.generic_relation_related_name
        self.assertTrue(value, name)
                         
        bak_registered_manager = Patient.objects 

        EavRegistry.unregister(Patient)
        
        self.assertEqual(type(Patient.objects), type(bak_registered_manager))
