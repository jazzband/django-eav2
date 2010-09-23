from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User
from django.db.models import Q

from ..models import *
from ..registry import Registry, EavConfig
from .models import Patient


class EavFilterTests(TestCase):

    """
        Testing filters
    """


    def setUp(self):
    
        Registry.unregister(Patient)
        Registry.register(Patient)

        self.attribute = Attribute.objects\
                                     .create(datatype=Attribute.TYPE_TEXT,
                                             name='City', slug='city')
                                                
        self.patient = Patient.objects.create(name="Doe")

        self.value = Value.objects.create(entity=self.patient,
                                             attribute=self.attribute,
                                             value_text='Denver')
                                             
    def tearDown(self):
        Registry.unregister(Patient)
        Registry.unregister(User)
        

    def additional_attribute_setup(self):
    
        self.country_attr = Attribute.objects\
                                .create(datatype=Attribute.TYPE_TEXT,
                                       name='Country', slug='country')

        class PatientEav(EavConfig):

            @classmethod
            def get_eav_attributes(cls):
                return Attribute.objects.filter(slug='country')
                
        self.PatientEav = PatientEav
                
        class UserEav(EavConfig):

            @classmethod
            def get_eav_attributes(cls):
                return Attribute.objects.all()
        
        self.UserEav = UserEav
        Registry.register(User, UserEav)
        self.user = User.objects.create(username='John')

       
    # todo: do that 
    #def test_can_filter_all_entities_by_value(self):
    
    #    self.additional_attribute_setup()
    #    self.user.eav.city = 'Paris'
    #    self.patient.eav.city = 'New York'
    #    self.user.save()
    #    self.patient.save()
        
        
        #print Entity.objects.filter(eav__city='Paris')
        
                         
    def test_you_can_filter_entity_by_attribute_values(self):
    
        self.additional_attribute_setup()
        self.user.eav.city = 'Paris'
        self.user.eav.country = None
        self.user.save()
        u = User.objects.create(username='Bob')
        u.eav.city = 'Paris'
        u.eav.country = 'France'
        u.save()
        u = User.objects.create(username='Jack')
        u.eav.city = 'New York'
        u.eav.country = 'Paris'
        u.save()
        u = User.objects.create(username='Fred')
        u.eav.city = 'Georgetown'
        u.eav.country = 'Guyana'
        u.save()
        
        '''

        This is what we have now:

        Username    City        Country
        --------    ----        -------
        John        Paris           
        Bob         Paris       France
        Jack        New York    Paris
        Fred        Georgetown  Guyana

        '''

        # There should be 2 users with a city of Paris (John and Bob)
        self.assertEqual(User.objects.filter(eav__city='Paris').count(), 2)

        # There should be 2 users with a city other than Paris (Jack and Fred)
        self.assertEqual(User.objects.exclude(eav__city='Paris').count(), 2)

        # This should only be Bob
        self.assertEqual(User.objects.filter(eav__city='Paris', 
                                            username='Bob').count(), 1)

        # This should be John, Jack, and Fred
        self.assertEqual(User.objects.exclude(eav__city='Paris', 
                                            username='Bob').count(), 3)


    def test_you_can_filter_entity_by_q_objects(self):
        self.additional_attribute_setup()
        self.user.eav.city = 'Paris'
        self.user.eav.country = None
        self.user.save()
        u = User.objects.create(username='Bob')
        u.eav.city = 'Paris'
        u.eav.country = 'France'
        u.save()
        u = User.objects.create(username='Jack')
        u.eav.city = 'New York'
        u.eav.country = 'Paris'
        u.save()
        u = User.objects.create(username='Fred')
        u.eav.city = 'Georgetown'
        u.eav.country = 'Guyana'
        u.save()
        
        '''

        This is what we have now:

        Username    City        Country
        --------    ----        -------
        John        Paris           
        Bob         Paris       France
        Jack        New York    Paris
        Fred        Georgetown  Guyana

        '''

        self.assertEqual(User.objects.filter(Q(username='Bob')).count(), 1)
        self.assertEqual(User.objects.exclude(Q(username='Bob')).count(), 3)

        self.assertEqual(User.objects.filter(Q(username='Bob') | Q(eav__country='Guyana')).count(), 2)

        self.assertEqual(User.objects.filter(Q(eav__city='Paris')).count(), 2)

        self.assertEqual(User.objects.exclude(eav__city='Paris').count(), 2)

        self.assertEqual(User.objects.filter(Q(eav__city='Paris') & \
                                             Q(username='Bob')).count(), 1)

        self.assertEqual(User.objects.filter(Q(eav__city='Paris', username='Jack')).count(), 0)

    def test_you_can_filter_entity_by_q_objects_with_lookups(self):
        class UserEav(EavConfig):
            manager_attr = 'eav_objects'
        Registry.register(User, UserEav)
        
        Attribute.objects.create(datatype=Attribute.TYPE_INT,
                                    name='Height')
        Attribute.objects.create(datatype=Attribute.TYPE_FLOAT,
                                    name='Weight')
        u = User.objects.create(username='Bob')
        u.eav.height = 10
        u.eav.weight = 20
        u.save()
        u = User.objects.create(username='Jack')
        u.eav.height = 20
        u.eav.weight = 10
        u.save()
        u = User.objects.create(username='Fred')
        u.eav.height = 15
        u.eav.weight = 15
        u.save()
        '''
        This is what we have now:

        Username    Hieght      Weight
        --------    ------      ------
        Bob          10          20           
        Jack         20          10
        Fred         15          15
        '''

        self.assertEqual(User.eav_objects.filter(eav__height__gt=12).count(), 2)
        self.assertEqual(User.eav_objects.filter(Q(eav__height__gt=12)).count(), 2)
        self.assertEqual(User.eav_objects.filter(eav__height__gte=20).count(), 1)
        self.assertEqual(User.eav_objects.filter(Q(eav__height__gte=20)).count(), 1)

        self.assertEqual(User.eav_objects.filter(Q(eav__height__gte=20) & Q(username='Fred')).count(), 0)
        self.assertEqual(User.eav_objects.filter(Q(eav__height=15) & Q(username='Fred')).count(), 1)

        self.assertEqual(User.eav_objects.filter(eav__height=20, eav__weight=10).count(), 1)

        self.assertEqual(User.eav_objects.filter(Q(eav__height=20) | Q(eav__weight=10) | Q(eav__weight=15)).count(), 2)

    def test_broken_eav_filters(self):
        '''
        This test demonstrates a few EAV queries that are known to be broken.
        it currently fails.
        '''
        Registry.register(User)
        
        Attribute.objects.create(datatype=Attribute.TYPE_INT,
                                 name='Height')

        Attribute.objects.create(datatype=Attribute.TYPE_FLOAT,
                                 name='Weight')

        u = User.objects.create(username='Bob')
        u.eav.height = 10
        u.eav.weight = 20
        u.eav.city = 'Paris'
        u.eav.country = 'France'
        u.save()
        u = User.objects.create(username='Jack')
        u.eav.height = 20
        u.eav.weight = 10
        u.eav.city = 'New York'
        u.eav.country = 'Paris'
        u.save()
        u = User.objects.create(username='Fred')
        u.eav.height = 15
        u.eav.weight = 15
        u.eav.city = 'Georgetown'
        u.eav.country = 'Guyana'
        u.save()

        self.assertEqual(User.objects.exclude(Q(eav__city='Paris')).count(), 2)
        self.assertEqual(User.objects.filter(Q(eav__height=20) & Q(eav__weight=10)).count(), 1)
        
        
