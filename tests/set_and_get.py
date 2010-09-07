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

        self.value = EavValue.objects.create(entity=self.patient,
                                             attribute=self.attribute,
                                             value_text='Denver')

    def tearDown(self):
        EavRegistry.unregister(Patient)
        
        
    def test_get_value_to_entity(self):
        self.assertEqual(self.attribute.get_value_for_entity(self.patient), 
                         self.value)
                         
                         
    def test_save_single_value(self):
        patient = Patient.objects.create(name="x")
        attr = EavAttribute.objects.create(datatype=EavAttribute.TYPE_TEXT,
                                            name='a', slug='a')
        # does nothing
        attr._save_single_value(patient)
        
        # save value
        attr._save_single_value(patient, 'b')
        patient = Patient.objects.get(name="x")
        self.assertEqual(patient.eav.a, 'b')
        
        # save value on another attribute
        attr._save_single_value(patient, 'Paris', self.attribute)
        patient = Patient.objects.get(name="x")
        self.assertEqual(patient.eav.city, 'Paris')
        

    def test_save_value(self):
        # TODO: update test_save_value when multiple values are out
        
        # save value
        self.attribute.save_value(self.patient, 'Paris')
        self.assertEqual(self.patient.eav.city, 'Paris')
        

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
        
        
    def test_you_can_create_several_type_of_attributes(self):
    
        EavAttribute.objects.create(datatype=EavAttribute.TYPE_TEXT,
                                    name='text', slug='text')
        EavAttribute.objects.create(datatype=EavAttribute.TYPE_FLOAT,
                                    name='float', slug='float')
        EavAttribute.objects.create(datatype=EavAttribute.TYPE_INT,
                                    name='int', slug='int')
        EavAttribute.objects.create(datatype=EavAttribute.TYPE_DATE,
                                    name='date', slug='date')   
        EavAttribute.objects.create(datatype=EavAttribute.TYPE_BOOLEAN,
                                    name='bool', slug='bool')    
                                 
        now = datetime.today()   
        self.patient.eav.text = 'a'   
        self.patient.eav.float = 1.0 
        self.patient.eav.int = 1 
        self.patient.eav.date = now
        self.patient.eav.bool = True
        
        self.patient.save()
        
        patient = Patient.objects.get(pk=self.patient.pk)
        self.assertEqual(self.patient.eav.float, 1.0)
        self.assertEqual(self.patient.eav.int, 1)
        self.assertEqual(self.patient.eav.date, now)
        self.assertEqual(self.patient.eav.bool, True)
        
        
    def test_assign_a_value_that_is_not_an_eav_attribute_does_nothing(self):
    
        self.patient.eav.no_an_attribute = 'Woot'
        self.patient.save()
        self.assertFalse(EavValue.objects.filter(value_text='Paris').count())
        
        
    def test_attributes_can_be_labelled(self):
    
        attribute = EavAttribute.objects\
                               .create(datatype=EavAttribute.TYPE_TEXT,
                                       name='Country', slug='country')
                                       
        # add labels
        self.attribute.add_label('a')
        self.attribute.add_label('c')
        attribute.add_label('b')
        attribute.add_label('c')
        
        self.assertEqual(EavAttribute.objects.get(labels__name='a').name, 
                        'City')
        self.assertEqual(EavAttribute.objects.get(labels__name='b').name, 
                        'Country')
                        
        # cross labels
        self.assertEqual(EavAttribute.objects.filter(labels__name='c').count(),
                         2)
            
        # remove labels             
        self.attribute.remove_label('a')
        self.assertFalse(EavAttribute.objects.filter(labels__name='a').count())
        # remove a label that is not attach does nothing
        self.attribute.remove_label('a')
        self.attribute.remove_label('x')
        
        
    def test_can_filter_attribute_availability_for_entity(self):
    
        attribute = EavAttribute.objects\
                                .create(datatype=EavAttribute.TYPE_TEXT,
                                       name='Country', slug='country')
    
        self.patient.eav.city = 'Paris'
        self.patient.save()
        self.assertEqual(Patient.objects.get(pk=self.patient.pk).eav.city,
                         'Paris')
    
        EavRegistry.unregister(Patient)

        class PatientEav(EavConfig):

            @classmethod
            def get_eav_attributes(cls):
                return EavAttribute.objects.filter(slug='country')
                
        EavRegistry.register(Patient, PatientEav)
        
        p = Patient.objects.create(name='Patrick')
        p.eav.city = 'Paris'
        p.eav.country = 'USA'
        p.save()
        p = Patient.objects.get(pk=self.patient.pk)
        
        self.assertFalse(p.eav.city)
        self.assertEqual(p.eav.country, 'USA')
        
        p = Patient()

        
