from django.test import TestCase
from django.db.models import Q
from django.contrib.auth.models import User

from ..registry import EavConfig
from ..models import EnumValue, EnumGroup, Attribute, Value

import eav
from .models import Patient, Encounter


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
        p1 = Patient.objects.get_or_create(name='Bob', eav__age=6)
        self.assertEqual(Patient.objects.get(eav__age=6), p1)
        p2 = Patient.objects.get_or_create(name='Fred', eav__age=6)
        self.assertRaises(Patient.MultipleObjectsReturned,
                          Patient.objects.get, eav__age=6)

    def test_filtering_on_normal_and_eav_fields(self):
        yes = self.yes
        no = self.no
        data = [
        #           Name      Age Fever City        Country
                [   'Bob',    12,  no,  'New York', 'USA'   ],
                [   'Fred',   15,  no,  'Bamako',   'Mali'  ],
                [   'Jose',   15,  yes, 'Kisumu',   'Kenya' ],
                [   'Joe',     2,  no,  'Nice',     'France'],
                [   'Beth',   21,  yes, 'France',   'Nice'  ]
        ]
        for row in data:
            Patient.objects.create(name=row[0], eav__age=row[1],
                                   eav__fever=row[2], eav__city=row[3],
                                   eav__country=row[4])

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

        # Joe
        q2 = Q(eav__age=2)
        self.assertEqual(Patient.objects.filter(q2).count(), 1)

        # Joe
        #self.assertEqual(Patient.objects.filter(q1 & q2).count(), 1)

        # Jose
        self.assertEqual(Patient.objects.filter(name__contains='J', eav__fever=yes).count(), 1)

    def test_eav_through_foreign_key(self):
        Patient.objects.create(name='Fred', eav__age=15)
        p = Patient.objects.create(name='Jon', eav__age=15)
        e = Encounter.objects.create(num=1, patient=p, eav__fever=self.yes)

        self.assertEqual(Patient.objects.filter(eav__age=15, encounter__eav__fever=self.yes).count(), 1)


    def test_manager_only_create(self):
        class UserEavConfig(EavConfig):
            manager_only = True

        eav.register(User, UserEavConfig)

        c = User.objects.create(username='joe')
