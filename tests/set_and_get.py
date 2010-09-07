from datetime import datetime

from django.test import TestCase

from ..models import *
from ..utils import EavRegistry, EavConfig
from .models import Patient


class EavSetterAndGetterTests(TestCase):

    """
        Testing setters and getters
    """


    def setUp(self):
    
        EavRegistry.unregister(Patient)
        EavRegistry.register(Patient)

        self.attribute = EavAttribute.objects\
                                     .create(datatype=EavAttribute.TYPE_TEXT,
                                             name='City', slug='city')
                                                
        self.patient = Patient.objects.create(name="Doe")

        self.value = EavValue.objects.create(object=self.patient,
                                             attribute=self.attribute,
                                             value_text='Denver')

    def tearDown(self):
        EavRegistry.unregister(Patient)
        

    def test_you_can_assign_a_value_to_an_unsaved_object(self):
        
        patient = Patient()
        patient.eav.city = 'Paris'
        patient.save()
        
        self.assertEqual(patient.eav.city, 'Paris')
        self.assertEqual(EavValue.objects.filter(value_text='Paris').count(), 1)
        
        
    def test_you_can_assign_a_value_to_a_saved_object(self):
        
        patient = Patient.objects.create(name='new_patient')
        patient.eav.city = 'Paris'
        patient.save()
        
        self.assertEqual(patient.eav.city, 'Paris')
        self.assertEqual(EavValue.objects.filter(value_text='Paris').count(), 1)
        
        
    def test_assign_a_value_that_is_not_an_eav_attribute_does_nothing(self):
    
        self.patient.eav.no_an_attribute = 'Woot'
        self.patient.save()
        self.assertFalse(EavValue.objects.filter(value_text='Paris').count())
        
        
    def test_attributes_can_be_labelled(self):
    
        attribute = EavAttribute.objects\
                               .create(datatype=EavAttribute.TYPE_TEXT,
                                       name='Country', slug='country')
        self.attribute.add_label('a')
        self.attribute.add_label('c')
        attribute.add_label('b')
        attribute.add_label('c')
        self.assertEqual(EavAttribute.objects.get(labels__name='a').name, 
                        'City')
        self.assertEqual(EavAttribute.objects.get(labels__name='b').name, 
                        'Country')
        self.assertEqual(EavAttribute.objects.filter(labels__name='c').count(),
                         2)
