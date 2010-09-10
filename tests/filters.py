from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User

from ..models import *
from ..utils import EavRegistry, EavConfig
from .models import Patient


class EavFilterTests(TestCase):

    """
        Testing filters
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
        EavRegistry.unregister(User)
        

    def additional_attribute_setup(self):
    
        self.country_attr = EavAttribute.objects\
                                .create(datatype=EavAttribute.TYPE_TEXT,
                                       name='Country', slug='country')

        class PatientEav(EavConfig):

            @classmethod
            def get_eav_attributes(cls):
                return EavAttribute.objects.filter(slug='country')
                
        self.PatientEav = PatientEav
                
        class UserEav(EavConfig):

            @classmethod
            def get_eav_attributes(cls):
                return EavAttribute.objects.filter(slug='city')
        
        self.UserEav = UserEav
        EavRegistry.register(User, UserEav)
        self.user = User.objects.create(username='John')

       
    # todo: do that 
    #def test_can_filter_all_entities_by_value(self):
    
    #    self.additional_attribute_setup()
    #    self.user.eav.city = 'Paris'
    #    self.patient.eav.city = 'New York'
    #    self.user.save()
    #    self.patient.save()
        
        
        #print EavEntity.objects.filter(eav__city='Paris')
        
                         
    def test_you_can_filter_entity_by_attribute_values(self):
    
        self.additional_attribute_setup()
        self.user.eav.city = 'Paris'
        self.user.save()
        u = User.objects.create(username='Bob')
        u.eav.city = "Paris"
        u.save()
        u = User.objects.create(username='Jack')
        u.eav.city = "New York"
        u.save()
        
        self.assertEqual(User.objects.filter(eav__city='Paris').count(), 2)
        self.assertEqual(User.objects.exclude(eav__city='Paris').count(), 1)
        self.assertEqual(User.objects.filter(eav__city='Paris', 
                                            username='Bob').count(), 1)
