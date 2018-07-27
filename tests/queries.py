from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q
from django.test import TestCase

import eav
from eav.models import Attribute, EnumGroup, EnumValue, Value

from .models import Encounter, Patient


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
        self.unknown = EnumValue.objects.create(value='unknown')

        ynu = EnumGroup.objects.create(name='Yes / No / Unknown')
        ynu.values.add(self.yes)
        ynu.values.add(self.no)
        ynu.values.add(self.unknown)

        Attribute.objects.create(name='fever', datatype=Attribute.TYPE_ENUM, enum_group=ynu)

    def tearDown(self):
        eav.unregister(Encounter)
        eav.unregister(Patient)

    def test_get_or_create_with_eav(self):
        Patient.objects.get_or_create(name='Bob', eav__age=5)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 1)
        Patient.objects.get_or_create(name='Bob', eav__age=5)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 1)
        Patient.objects.get_or_create(name='Bob', eav__age=6)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(Value.objects.count(), 2)

    def test_get_with_eav(self):
        p1, _ = Patient.objects.get_or_create(name='Bob', eav__age=6)
        self.assertEqual(Patient.objects.get(eav__age=6), p1)

        Patient.objects.create(name='Fred', eav__age=6)
        self.assertRaises(MultipleObjectsReturned, lambda: Patient.objects.get(eav__age=6))

    def test_filtering_on_normal_and_eav_fields(self):
        yes = self.yes
        no = self.no

        data = [
            # Name,    age, fever, city,       country.
            ['Anne',   3,   no,    'New York', 'USA'],
            ['Bob',    15,  no,    'Bamako',   'Mali'],
            ['Cyrill', 15,  yes,   'Kisumu',   'Kenya'],
            ['Daniel', 3,   no,    'Nice',     'France'],
            ['Eugene', 2,   yes,   'France',   'Nice']
        ]

        for row in data:
            Patient.objects.create(
                name=row[0],
                eav__age=row[1],
                eav__fever=row[2],
                eav__city=row[3],
                eav__country=row[4]
            )

        # Check number of objects in DB.
        self.assertEqual(Patient.objects.count(), 5)
        self.assertEqual(Value.objects.count(), 20)

        # Nobody
        q1 = Q(eav__fever=yes) & Q(eav__fever=no)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 0)

        # Anne, Daniel
        q1 = Q(eav__age__gte=3)        # Everyone except Eugene
        q2 = Q(eav__age__lt=15)        # Anne, Daniel, Eugene
        p = Patient.objects.filter(q2 & q1)
        self.assertEqual(p.count(), 2)

        # Anne
        q1 = Q(eav__city__contains='Y') & Q(eav__fever=no)
        q2 = Q(eav__age=3)
        p = Patient.objects.filter(q1 & q2)
        self.assertEqual(p.count(), 1)

        # Anne, Daniel
        q1 = Q(eav__city__contains='Y', eav__fever=no)
        q2 = Q(eav__city='Nice')
        q3 = Q(eav__age=3)
        p = Patient.objects.filter((q1 | q2) & q3)
        self.assertEqual(p.count(), 2)

        # Everyone
        q1 = Q(eav__fever=no) | Q(eav__fever=yes)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 5)

        # Anne, Bob, Daniel
        q1 = Q(eav__fever=no)              # Anne, Bob, Daniel
        q2 = Q(eav__fever=yes)             # Cyrill, Eugene
        q3 = Q(eav__country__contains='e') # Cyrill, Daniel, Eugene
        q4 = q2 & q3                       # Cyrill, Daniel, Eugene
        q5 = (q1 | q4) & q1                # Anne, Bob, Daniel
        p = Patient.objects.filter(q5)
        self.assertEqual(p.count(), 3)

        # Everyone except Anne
        q1 = Q(eav__city__contains='Y')
        p = Patient.objects.exclude(q1)
        self.assertEqual(p.count(), 4)

        # Anne, Bob, Daniel
        q1 = Q(eav__city__contains='Y')
        q2 = Q(eav__fever=no)
        q3 = q1 | q2
        p = Patient.objects.filter(q3)
        self.assertEqual(p.count(), 3)

        # Anne, Daniel
        q1 = Q(eav__age=3)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 2)

        # Eugene
        q1 = Q(name__contains='E', eav__fever=yes)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 1)
