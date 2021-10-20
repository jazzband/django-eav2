from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from django.db.utils import NotSupportedError
from django.test import TestCase

import eav
from eav.models import Attribute, EnumGroup, EnumValue, Value
from eav.registry import EavConfig
from test_project.models import Encounter, Patient


class Queries(TestCase):
    def setUp(self):
        eav.register(Encounter)
        eav.register(Patient)

        Attribute.objects.create(name='age', datatype=Attribute.TYPE_INT)
        Attribute.objects.create(name='height', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='weight', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='city', datatype=Attribute.TYPE_TEXT)
        Attribute.objects.create(name='country', datatype=Attribute.TYPE_TEXT)
        Attribute.objects.create(name='extras', datatype=Attribute.TYPE_JSON)
        Attribute.objects.create(name='illness', datatype=Attribute.TYPE_CSV)

        self.yes = EnumValue.objects.create(value='yes')
        self.no = EnumValue.objects.create(value='no')
        self.unknown = EnumValue.objects.create(value='unknown')

        ynu = EnumGroup.objects.create(name='Yes / No / Unknown')
        ynu.values.add(self.yes)
        ynu.values.add(self.no)
        ynu.values.add(self.unknown)

        Attribute.objects.create(
            name='fever', datatype=Attribute.TYPE_ENUM, enum_group=ynu
        )

    def tearDown(self):
        eav.unregister(Encounter)
        eav.unregister(Patient)

    def init_data(self):
        yes = self.yes
        no = self.no

        data = [
            # Name, age, fever,
            # city, country, extras
            # possible illness
            ['Anne', 3, no, 'New York', 'USA', {"chills": "yes"}, "cold"],
            ['Bob', 15, no, 'Bamako', 'Mali', {}, ""],
            [
                'Cyrill',
                15,
                yes,
                'Kisumu',
                'Kenya',
                {"chills": "yes", "headache": "no"},
                "flu",
            ],
            ['Daniel', 3, no, 'Nice', 'France', {"headache": "yes"}, "cold"],
            [
                'Eugene',
                2,
                yes,
                'France',
                'Nice',
                {"chills": "no", "headache": "yes"},
                "flu;cold",
            ],
        ]

        for row in data:
            Patient.objects.create(
                name=row[0],
                eav__age=row[1],
                eav__fever=row[2],
                eav__city=row[3],
                eav__country=row[4],
                eav__extras=row[5],
                eav__illness=row[6],
            )

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

    def test_get_or_create_with_defaults(self):
        """Tests EntityManager.get_or_create() with defaults keyword."""
        city_name = 'Tokyo'
        email = 'mari@test.com'
        p1, _ = Patient.objects.get_or_create(
            name='Mari',
            eav__age=27,
            defaults={
                'email': email,
                'eav__city': city_name,
            },
        )
        assert Patient.objects.count() == 1
        assert p1.email == email
        assert p1.eav.city == city_name

    def test_get_with_eav(self):
        p1, _ = Patient.objects.get_or_create(name='Bob', eav__age=6)
        self.assertEqual(Patient.objects.get(eav__age=6), p1)

        Patient.objects.create(name='Fred', eav__age=6)
        self.assertRaises(
            MultipleObjectsReturned, lambda: Patient.objects.get(eav__age=6)
        )

    def test_filtering_on_normal_and_eav_fields(self):
        self.init_data()

        # Check number of objects in DB.
        self.assertEqual(Patient.objects.count(), 5)
        self.assertEqual(Value.objects.count(), 29)

        # Nobody
        q1 = Q(eav__fever=self.yes) & Q(eav__fever=self.no)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 0)

        # Anne, Daniel
        q1 = Q(eav__age__gte=3)  # Everyone except Eugene
        q2 = Q(eav__age__lt=15)  # Anne, Daniel, Eugene
        p = Patient.objects.filter(q2 & q1)
        self.assertEqual(p.count(), 2)

        # Anne
        q1 = Q(eav__city__contains='Y') & Q(eav__fever='no')
        q2 = Q(eav__age=3)
        p = Patient.objects.filter(q1 & q2)
        self.assertEqual(p.count(), 1)

        # Anne
        q1 = Q(eav__city__contains='Y') & Q(eav__fever=self.no)
        q2 = Q(eav__age=3)
        p = Patient.objects.filter(q1 & q2)
        self.assertEqual(p.count(), 1)

        # Anne, Daniel
        q1 = Q(eav__city__contains='Y', eav__fever=self.no)
        q2 = Q(eav__city='Nice')
        q3 = Q(eav__age=3)
        p = Patient.objects.filter((q1 | q2) & q3)
        self.assertEqual(p.count(), 2)

        # Everyone
        q1 = Q(eav__fever=self.no) | Q(eav__fever=self.yes)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 5)

        # Anne, Bob, Daniel
        q1 = Q(eav__fever=self.no)  # Anne, Bob, Daniel
        q2 = Q(eav__fever=self.yes)  # Cyrill, Eugene
        q3 = Q(eav__country__contains='e')  # Cyrill, Daniel, Eugene
        q4 = q2 & q3  # Cyrill, Daniel, Eugene
        q5 = (q1 | q4) & q1  # Anne, Bob, Daniel
        p = Patient.objects.filter(q5)
        self.assertEqual(p.count(), 3)

        # Everyone except Anne
        q1 = Q(eav__city__contains='Y')
        p = Patient.objects.exclude(q1)
        self.assertEqual(p.count(), 4)

        # Anne, Bob, Daniel
        q1 = Q(eav__city__contains='Y')
        q2 = Q(eav__fever=self.no)
        q3 = q1 | q2
        p = Patient.objects.filter(q3)
        self.assertEqual(p.count(), 3)

        # Anne, Daniel
        q1 = Q(eav__age=3)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 2)

        # Eugene
        q1 = Q(name__contains='E', eav__fever=self.yes)
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 1)

        # Extras: Chills
        # Without
        q1 = Q(eav__extras__has_key="chills")
        p = Patient.objects.exclude(q1)
        self.assertEqual(p.count(), 2)

        # With
        q1 = Q(eav__extras__has_key="chills")
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 3)

        # No chills
        q1 = Q(eav__extras__chills="no")
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 1)

        # Has chills
        q1 = Q(eav__extras__chills="yes")
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 2)

        # Extras: Empty
        # Yes
        q1 = Q(eav__extras={})
        p = Patient.objects.filter(q1)
        self.assertEqual(p.count(), 1)

        # No
        q1 = Q(eav__extras={})
        p = Patient.objects.exclude(q1)
        self.assertEqual(p.count(), 4)

        # Illness:
        # Cold
        q1 = Q(eav__illness__icontains="cold")
        p = Patient.objects.exclude(q1)
        self.assertEqual(p.count(), 2)

        # Flu
        q1 = Q(eav__illness__icontains="flu")
        p = Patient.objects.exclude(q1)
        self.assertEqual(p.count(), 3)

        # Empty
        q1 = Q(eav__illness__isnull=False)
        p = Patient.objects.filter(~q1)
        self.assertEqual(p.count(), 1)

    def _order(self, ordering):
        query = Patient.objects.all().order_by(*ordering)
        return list(query.values_list('name', flat=True))

    def assert_order_by_results(self, eav_attr='eav'):
        self.assertEqual(
            ['Bob', 'Eugene', 'Cyrill', 'Anne', 'Daniel'],
            self._order(['%s__city' % eav_attr]),
        )

        self.assertEqual(
            ['Eugene', 'Anne', 'Daniel', 'Bob', 'Cyrill'],
            self._order(['%s__age' % eav_attr, '%s__city' % eav_attr]),
        )

        self.assertEqual(
            ['Eugene', 'Cyrill', 'Anne', 'Daniel', 'Bob'],
            self._order(['%s__fever' % eav_attr, '%s__age' % eav_attr]),
        )

        self.assertEqual(
            ['Eugene', 'Cyrill', 'Daniel', 'Bob', 'Anne'],
            self._order(['%s__fever' % eav_attr, '-name']),
        )

        self.assertEqual(
            ['Eugene', 'Daniel', 'Cyrill', 'Bob', 'Anne'],
            self._order(['-name', '%s__age' % eav_attr]),
        )

        self.assertEqual(
            ['Anne', 'Bob', 'Cyrill', 'Daniel', 'Eugene'],
            self._order(['example__name']),
        )

        with self.assertRaises(NotSupportedError):
            Patient.objects.all().order_by('%s__first__second' % eav_attr)

        with self.assertRaises(ObjectDoesNotExist):
            Patient.objects.all().order_by('%s__nonsense' % eav_attr)

    def test_order_by(self):
        self.init_data()
        self.assert_order_by_results()

    def test_order_by_with_custom_config(self):
        class CustomConfig(EavConfig):
            eav_attr = "data"
            generic_relation_attr = "data_values"

        self.init_data()
        eav.unregister(Patient)
        eav.register(Patient, config_cls=CustomConfig)
        self.assert_order_by_results(eav_attr='data')
