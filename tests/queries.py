from django.test import TestCase
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned

import eav
from eav.registry import EavConfig
from eav.models import EnumValue, EnumGroup, Attribute, Value

from .models import Patient, Encounter, ExampleModel


class Queries(TestCase):
    def setUp(self):
        eav.register(Encounter)
        eav.register(Patient)

        Attribute.objects.create(name='age', datatype=Attribute.TYPE_INT)
        Attribute.objects.create(name='height', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='weight', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='city', datatype=Attribute.TYPE_TEXT)
        Attribute.objects.create(name='country', datatype=Attribute.TYPE_TEXT)

        self.yes = EnumValue.objects.create(value='yes')
        self.no = EnumValue.objects.create(value='no')
        self.unkown = EnumValue.objects.create(value='unkown')
        
        ynu = EnumGroup.objects.create(name='Yes / No / Unknown')
        ynu.enums.add(self.yes)
        ynu.enums.add(self.no)
        ynu.enums.add(self.unkown)
        
        Attribute.objects.create(name='fever', datatype=Attribute.TYPE_ENUM, enum_group=ynu)

    def tearDown(self):
        eav.unregister(Encounter)
        eav.unregister(Patient)

    def test_get_or_create_with_eav(self):
        return
        p = Patient.objects.get_or_create(name='Bob', eav__age=5)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 1)
        p = Patient.objects.get_or_create(name='Bob', eav__age=5)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 1)
        p = Patient.objects.get_or_create(name='Bob', eav__age=6)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(Value.objects.count(), 2)

    def test_get_with_eav(self):
        return
        p1, _ = Patient.objects.get_or_create(name='Bob', eav__age=6)
        self.assertEqual(Patient.objects.get(eav__age=6), p1)
        
        p2, _ = Patient.objects.get_or_create(name='Fred', eav__age=6)
        self.assertRaises(MultipleObjectsReturned, lambda: Patient.objects.get(eav__age=6))

    def test_filtering_on_normal_and_eav_fields(self):       
        yes = self.yes
        no = self.no
        data = [
            ['3_New_York_USA', 3, no, 'New York', 'USA'],
            ['15_Bamako_Mali', 15, no, 'Bamako', 'Mali'],
            ['15_Kisumu_Kenya', 15, yes, 'Kisumu', 'Kenya'],
            ['3_Nice_France', 3, no, 'Nice', 'France'],
            ['2_France_Nice', 2, yes, 'France', 'Nice']
        ]
        
        for row in data:
            Patient.objects.create(
                name=row[0],
                eav__age=row[1],
                eav__fever=row[2],
                eav__city=row[3],
                eav__country=row[4]
            )

        #1 = Q(eav__city__contains='Y') & Q(eav__fever=no)
        #2 = Q(eav__age=3)
        #3 = (q1 & q2)
        #rint(vars(q3))
        
        # = Patient.objects.filter(q3)
        #print(q)
            
        # return
        self.assertEqual(Patient.objects.count(), 5)
        self.assertEqual(Value.objects.count(), 20)

        self.assertEqual(Patient.objects.filter(eav__city__contains='Y').count(), 1)
        self.assertEqual(Patient.objects.exclude(eav__city__contains='Y').count(), 4)

        # Bob
        self.assertEqual(Patient.objects.filter(Q(eav__city__contains='Y')).count(), 1)

        # Everyone except Bob
        #self.assertEqual(Patient.objects.exclude(Q(eav__city__contains='Y')).count(), 4)

        # Bob, Fred, Joe
        q1 = Q(eav__city__contains='Y') |  Q(eav__fever=no)
        self.assertEqual(Patient.objects.filter(q1).count(), 3)

        # Joe, Bob
        q2 = Q(eav__age=3)
        self.assertEqual(Patient.objects.filter(q2).count(), 2)

        # Joe, Bob
        #elf.assertEqual(Patient.objects.filter(q1 & q2).count(), 1)

        # Jose
        self.assertEqual(Patient.objects.filter(name__contains='F', eav__fever=yes).count(), 1)

