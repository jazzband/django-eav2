from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User

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
 

    def test_underscore_prevent_a_data_from_been_saved(self):
        
        patient = Patient.objects.create(name='new_patient')
        patient.eav._test = 'Paris'
        patient.save()
        
        patient = Patient.objects.get(name='new_patient')
        try:
            patient.eav._test
            self.fail()
        except AttributeError:
            pass
        self.assertFalse(EavValue.objects.filter(value_text='Paris').count())
               
        
    def test_you_can_create_several_type_of_attributes(self):
    
        self.patient = Patient(name='test')
    
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
        EavAttribute.objects.create(datatype=EavAttribute.TYPE_OBJECT,
                                    name='object', slug='object')   
                                 
        now = datetime.today()   
        self.patient.eav.text = 'a'   
        self.patient.eav.float = 1.0 
        self.patient.eav.int = 1 
        self.patient.eav.date = now
        self.patient.eav.bool = True
        self.patient.eav.object = User.objects.create(username='Bob')
        
        self.patient.save()
        
        patient = Patient.objects.get(pk=self.patient.pk)
        self.assertEqual(self.patient.eav.float, 1.0)
        self.assertEqual(self.patient.eav.int, 1)
        self.assertEqual(self.patient.eav.date, now)
        self.assertEqual(self.patient.eav.bool, True)
        self.assertEqual(self.patient.eav.object, 
                         User.objects.get(username='Bob'))
        
        
    def test_assign_a_value_that_is_not_an_eav_attribute_does_nothing(self):
    
        self.patient.eav.no_an_attribute = 'Woot'
        self.patient.save()
        self.assertFalse(EavValue.objects.filter(value_text='Paris').count())
      
          
    def test_get_a_value_that_does_not_exists(self):
    
        # return None for non '_' values
        self.assertEqual(self.patient.eav.impossible_value, None) 
        
        # normal behavior for '_' values
        try:
            self.patient.eav._impossible_value
            self.fail()
        except AttributeError:
            pass
        
        
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
        


    def test_attributes_are_filtered_according_to_config_class(self):

        self.additional_attribute_setup()
                
        EavRegistry.unregister(Patient)
        EavRegistry.register(Patient, self.PatientEav)
        EavRegistry.register(User, self.UserEav)

        self.assertEqual(list(Patient.eav.get_eav_attributes()),
                         list(EavAttribute.objects.filter(slug='country')))
                        
        self.assertEqual(list(User.eav.get_eav_attributes()),
                         list(EavAttribute.objects.filter(slug='city')))
        
        
    def test_can_filter_attribute_availability_for_entity(self):
        
        self.additional_attribute_setup()
        
        self.patient.eav.city = 'Tunis'
        self.patient.save()
        self.assertEqual(Patient.objects.get(pk=self.patient.pk).eav.city,
                         'Tunis')

        EavRegistry.unregister(Patient)
        EavRegistry.register(Patient, self.PatientEav)
        
        p = Patient.objects.create(name='Patrick')
        p.eav.city = 'Paris'
        p.eav.country = 'USA'
        p.save()
        p = Patient.objects.get(pk=p.pk)

        self.assertFalse(p.eav.city, 'Paris')
        self.assertEqual(p.eav.country, 'USA')
        

    def test_can_have_differente_attribute_filter(self):
    
        self.additional_attribute_setup()
    
        EavRegistry.unregister(Patient)
        EavRegistry.register(Patient, self.PatientEav)
        EavRegistry.register(User, self.UserEav)
        
        p = Patient.objects.create(name='Patrick')
        u = User.objects.create(username='John')
        
        p.eav.city = 'Paris'
        p.eav.country = 'USA'
        p.save()
        u.eav.city = 'Paris'
        u.eav.country = 'USA'
        u.save()
        
        p = Patient.objects.get(pk=p.pk)
        u = User.objects.get(pk=u.pk)
        
        self.assertFalse(p.eav.city)
        self.assertEqual(p.eav.country, 'USA')

        self.assertFalse(u.eav.country)
        self.assertEqual(u.eav.city, 'Paris')


    def test_can_have_a_subclass_for_config_class(self):
    
        self.additional_attribute_setup()
    
        EavRegistry.unregister(Patient)

        class SubPatientEav(self.PatientEav):       
        
            @classmethod
            def get_eav_attributes(cls):
                return EavAttribute.objects.filter(slug='country')
                
        EavRegistry.register(Patient, SubPatientEav)
        
        self.patient.eav.city = 'Paris'
        self.patient.eav.country = 'USA'
        self.patient.save()
        
        p = Patient.objects.get(pk=self.patient.pk)
        
        self.assertFalse(p.eav.city)
        self.assertEqual(p.eav.country, 'USA')

        
    def test_blank_set_all_value_field_with_a_null_default_to_none(self):
        self.value._blank()
        self.assertEqual(self.value.value_text, None)
        self.assertEqual(self.value.value_int, None)
        self.assertEqual(self.value.value_float, None)
        self.assertEqual(self.value.value_date, None)
        self.assertEqual(self.value.value_object, None)
        self.assertEqual(self.value.value_bool, None)
        
    
    def test_get_value_on_eavvalue_return_python_object(self):
        self.assertEqual(self.value._get_value(), 'Denver')
        self.assertEqual(self.value.value, self.value._get_value())
        
        
    def test_set_value_store_the_python_object_and_blank_other_fields(self):
        
        self.value._set_value('Bamako')
        self.assertEqual(self.value.value, 'Bamako')
        self.assertEqual(self.value.value_text, 'Bamako')
        self.assertEqual(self.value.value_int, None)
        self.assertEqual(self.value.value_float, None)
        self.assertEqual(self.value.value_date, None)
        self.assertEqual(self.value.value_bool, None)
        self.assertEqual(self.value.value_object, None)
        
        
    def test_get_eav_attributes(self):
    
        self.additional_attribute_setup()
        EavRegistry.unregister(Patient)
        EavRegistry.register(Patient, self.PatientEav)
        
        assert list(self.PatientEav.get_eav_attributes_for_model(Patient))\
               == list(EavEntity.get_eav_attributes_for_model(Patient))\
               == list(self.patient.eav.get_eav_attributes())\
               == list(Patient.eav.get_eav_attributes_for_model(Patient))\
               == list(EavAttribute.objects.filter(slug='country'))
               
               
    def test_values(self):
        self.additional_attribute_setup()
        self.patient.eav.city = 'Beijin'
        self.patient.eav.coutry = 'China'
        self.patient.save()
        
        self.assertEqual(list(self.patient.eav.get_values()),
                         list(EavValue.objects.exclude(value_text='Denver')))
     
     
    def test_get_all_attribute_slugs_for_model(self):
        
        self.country_attr = EavAttribute.objects\
                                .create(datatype=EavAttribute.TYPE_TEXT,
                                       name='Street', slug='street')
                                       
        self.additional_attribute_setup()
        
        class UserEav(EavConfig):

            @classmethod
            def get_eav_attributes(cls):
                return EavAttribute.objects.exclude(slug='city')
        
        EavRegistry.register(User, UserEav)
        
        u = User.objects.create(username='John')
        
        slugs = dict((s.slug, s) for s in EavAttribute.objects\
                                                     .exclude(slug='city'))
                                                      
        assert slugs\
               == EavEntity.get_all_attribute_slugs_for_model(User)\
               == User.eav.get_all_attribute_slugs_for_model(User)\
               == u.eav.get_all_attribute_slugs()
        
        
    def test_iteration(self):
        self.additional_attribute_setup()
        self.patient.eav.country = 'Kenya'
        self.patient.eav.save()
        
        self.assertEqual(list(EavValue.objects.all()),
                         list(Patient.objects.get(pk=self.patient.pk).eav))
                         
               
