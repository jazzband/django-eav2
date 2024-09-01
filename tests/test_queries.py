from __future__ import annotations

import pytest
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from django.db.utils import NotSupportedError
from django.test import TestCase

import eav
from eav.models import Attribute, EnumGroup, EnumValue, Value
from eav.registry import EavConfig
from test_project.models import Encounter, ExampleModel, Patient


class Queries(TestCase):
    def setUp(self):
        eav.register(Encounter)
        eav.register(Patient)

        Attribute.objects.create(name="age", datatype=Attribute.TYPE_INT)
        Attribute.objects.create(name="height", datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name="weight", datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name="city", datatype=Attribute.TYPE_TEXT)
        Attribute.objects.create(name="country", datatype=Attribute.TYPE_TEXT)
        Attribute.objects.create(name="extras", datatype=Attribute.TYPE_JSON)
        Attribute.objects.create(name="illness", datatype=Attribute.TYPE_CSV)

        self.yes = EnumValue.objects.create(value="yes")
        self.no = EnumValue.objects.create(value="no")
        self.unknown = EnumValue.objects.create(value="unknown")

        ynu = EnumGroup.objects.create(name="Yes / No / Unknown")
        ynu.values.add(self.yes)
        ynu.values.add(self.no)
        ynu.values.add(self.unknown)

        Attribute.objects.create(
            name="fever",
            datatype=Attribute.TYPE_ENUM,
            enum_group=ynu,
        )

    def tearDown(self):
        eav.unregister(Encounter)
        eav.unregister(Patient)

    def init_data(self) -> None:
        yes = self.yes
        no = self.no

        data = [
            # Name, age, fever,
            # city, country, extras
            # possible illness
            ["Anne", 3, no, "New York", "USA", {"chills": "yes"}, "cold"],
            ["Bob", 15, no, "Bamako", "Mali", {}, ""],
            [
                "Cyrill",
                15,
                yes,
                "Kisumu",
                "Kenya",
                {"chills": "yes", "headache": "no"},
                "flu",
            ],
            ["Daniel", 3, no, "Nice", "France", {"headache": "yes"}, "cold"],
            [
                "Eugene",
                2,
                yes,
                "France",
                "Nice",
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
        Patient.objects.get_or_create(name="Bob", eav__age=5)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 1)
        Patient.objects.get_or_create(name="Bob", eav__age=5)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Value.objects.count(), 1)
        Patient.objects.get_or_create(name="Bob", eav__age=6)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(Value.objects.count(), 2)

    def test_get_or_create_with_defaults(self):
        """Tests EntityManager.get_or_create() with defaults keyword."""
        city_name = "Tokyo"
        email = "mari@test.com"
        p1, _ = Patient.objects.get_or_create(
            name="Mari",
            eav__age=27,
            defaults={
                "email": email,
                "eav__city": city_name,
            },
        )
        assert Patient.objects.count() == 1
        assert p1.email == email
        assert p1.eav.city == city_name

    def test_get_with_eav(self):
        p1, _ = Patient.objects.get_or_create(name="Bob", eav__age=6)
        self.assertEqual(Patient.objects.get(eav__age=6), p1)

        Patient.objects.create(name="Fred", eav__age=6)
        self.assertRaises(
            MultipleObjectsReturned,
            lambda: Patient.objects.get(eav__age=6),
        )

    def test_no_results_for_contradictory_conditions(self) -> None:
        """Test that contradictory conditions return no results."""
        self.init_data()
        q1 = Q(eav__fever=self.yes) & Q(eav__fever=self.no)
        p = Patient.objects.filter(q1)

        # Should return no patients due to contradictory conditions
        assert p.count() == 0

    def test_filtering_on_numeric_eav_fields(self) -> None:
        """Test filtering on numeric EAV fields."""
        self.init_data()
        q1 = Q(eav__age__gte=3)  # Everyone except Eugene
        q2 = Q(eav__age__lt=15)  # Anne, Daniel, Eugene
        p = Patient.objects.filter(q2 & q1)

        # Should return Anne and Daniel
        assert p.count() == 2

    def test_filtering_on_text_and_boolean_eav_fields(self) -> None:
        """Test filtering on text and boolean EAV fields."""
        self.init_data()
        q1 = Q(eav__city__contains="Y") & Q(eav__fever="no")
        q2 = Q(eav__age=3)
        p = Patient.objects.filter(q1 & q2)

        # Should return only Anne
        assert p.count() == 1

    def test_filtering_with_enum_eav_fields(self) -> None:
        """Test filtering with enum EAV fields."""
        self.init_data()
        q1 = Q(eav__city__contains="Y") & Q(eav__fever=self.no)
        q2 = Q(eav__age=3)
        p = Patient.objects.filter(q1 & q2)

        # Should return only Anne
        assert p.count() == 1

    def test_complex_query_with_or_conditions(self) -> None:
        """Test complex query with OR conditions."""
        self.init_data()
        q1 = Q(eav__city__contains="Y", eav__fever=self.no)
        q2 = Q(eav__city="Nice")
        q3 = Q(eav__age=3)
        p = Patient.objects.filter((q1 | q2) & q3)

        # Should return Anne and Daniel
        assert p.count() == 2

    def test_filtering_with_multiple_enum_values(self) -> None:
        """Test filtering with multiple enum values."""
        self.init_data()
        q1 = Q(eav__fever=self.no) | Q(eav__fever=self.yes)
        p = Patient.objects.filter(q1)

        # Should return all patients
        assert p.count() == 5

    def test_complex_query_with_multiple_conditions(self) -> None:
        """Test complex query with multiple conditions."""
        self.init_data()
        q1 = Q(eav__fever=self.no)  # Anne, Bob, Daniel
        q2 = Q(eav__fever=self.yes)  # Cyrill, Eugene
        q3 = Q(eav__country__contains="e")  # Cyrill, Daniel, Eugene
        q4 = q2 & q3  # Cyrill, Daniel, Eugene
        q5 = (q1 | q4) & q1  # Anne, Bob, Daniel
        p = Patient.objects.filter(q5)

        # Should return Anne, Bob, and Daniel
        assert p.count() == 3

    def test_excluding_with_eav_fields(self) -> None:
        """Test excluding with EAV fields."""
        self.init_data()
        q1 = Q(eav__city__contains="Y")
        p = Patient.objects.exclude(q1)

        # Should return all patients except Anne
        assert p.count() == 4

    def test_filtering_with_or_conditions(self) -> None:
        """Test filtering with OR conditions."""
        self.init_data()
        q1 = Q(eav__city__contains="Y")
        q2 = Q(eav__fever=self.no)
        q3 = q1 | q2
        p = Patient.objects.filter(q3)

        # Should return Anne, Bob, and Daniel
        assert p.count() == 3

    def test_filtering_on_single_eav_field(self) -> None:
        """Test filtering on a single EAV field."""
        self.init_data()
        q1 = Q(eav__age=3)
        p = Patient.objects.filter(q1)

        # Should return Anne and Daniel
        assert p.count() == 2

    def test_combining_normal_and_eav_fields(self) -> None:
        """Test combining normal and EAV fields in a query."""
        self.init_data()
        q1 = Q(name__contains="E", eav__fever=self.yes)
        p = Patient.objects.filter(q1)

        # Should return only Eugene
        assert p.count() == 1

    def test_filtering_on_json_eav_field(self) -> None:
        """Test filtering on JSON EAV field."""
        self.init_data()
        q1 = Q(eav__extras__has_key="chills")
        p = Patient.objects.exclude(q1)

        # Should return patients without 'chills' in extras
        assert p.count() == 2

        q1 = Q(eav__extras__has_key="chills")
        p = Patient.objects.filter(q1)

        # Should return patients with 'chills' in extras
        assert p.count() == 3

        q1 = Q(eav__extras__chills="no")
        p = Patient.objects.filter(q1)

        # Should return patients with 'chills' set to 'no'
        assert p.count() == 1

        q1 = Q(eav__extras__chills="yes")
        p = Patient.objects.filter(q1)

        # Should return patients with 'chills' set to 'yes'
        assert p.count() == 2

    def test_filtering_on_empty_json_eav_field(self) -> None:
        """Test filtering on empty JSON EAV field."""
        self.init_data()
        q1 = Q(eav__extras={})
        p = Patient.objects.filter(q1)

        # Should return patients with empty extras
        assert p.count() == 1

        q1 = Q(eav__extras={})
        p = Patient.objects.exclude(q1)

        # Should return patients with non-empty extras
        assert p.count() == 4

    def test_filtering_on_text_eav_field_with_icontains(self) -> None:
        """Test filtering on text EAV field with icontains."""
        self.init_data()
        q1 = Q(eav__illness__icontains="cold")
        p = Patient.objects.exclude(q1)

        # Should return patients without 'cold' in illness
        assert p.count() == 2

        q1 = Q(eav__illness__icontains="flu")
        p = Patient.objects.exclude(q1)

        # Should return patients without 'flu' in illness
        assert p.count() == 3

    def test_filtering_on_null_eav_field(self) -> None:
        """Test filtering on null EAV field."""
        self.init_data()
        q1 = Q(eav__illness__isnull=False)
        p = Patient.objects.filter(~q1)

        # Should return patients with null illness
        assert p.count() == 1

    def _order(self, ordering) -> list[str]:
        query = Patient.objects.all().order_by(*ordering)
        return list(query.values_list("name", flat=True))

    def assert_order_by_results(self, eav_attr="eav") -> None:
        """Test the ordering functionality of EAV attributes."""
        # Ordering by a single EAV attribute
        assert self._order([f"{eav_attr}__city"]) == [
            "Bob",
            "Eugene",
            "Cyrill",
            "Anne",
            "Daniel",
        ]

        # Ordering by multiple EAV attributes
        assert self._order([f"{eav_attr}__age", f"{eav_attr}__city"]) == [
            "Eugene",
            "Anne",
            "Daniel",
            "Bob",
            "Cyrill",
        ]

        # Ordering by EAV attributes with different data types
        assert self._order([f"{eav_attr}__fever", f"{eav_attr}__age"]) == [
            "Eugene",
            "Cyrill",
            "Anne",
            "Daniel",
            "Bob",
        ]

        # Combining EAV and regular model field ordering
        assert self._order([f"{eav_attr}__fever", "-name"]) == [
            "Eugene",
            "Cyrill",
            "Daniel",
            "Bob",
            "Anne",
        ]

        # Mixing regular and EAV field ordering
        assert self._order(["-name", f"{eav_attr}__age"]) == [
            "Eugene",
            "Daniel",
            "Cyrill",
            "Bob",
            "Anne",
        ]

        # Ordering by a related model field
        assert self._order(["example__name"]) == [
            "Anne",
            "Bob",
            "Cyrill",
            "Daniel",
            "Eugene",
        ]

        # Error handling for unsupported nested EAV attributes
        with pytest.raises(NotSupportedError):
            Patient.objects.all().order_by(f"{eav_attr}__first__second")

        # Error handling for non-existent EAV attributes
        with pytest.raises(ObjectDoesNotExist):
            Patient.objects.all().order_by(f"{eav_attr}__nonsense")

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
        self.assert_order_by_results(eav_attr="data")

    def test_fk_filter(self):
        e = ExampleModel.objects.create(name="test1")
        p = Patient.objects.get_or_create(name="Beth", example=e)[0]
        c = ExampleModel.objects.filter(patient=p)
        self.assertEqual(c.count(), 1)

    def test_filter_with_multiple_eav_attributes(self):
        """
        Test filtering a model using both regular and multiple EAV attributes.

        This test initializes test data and then filters the Patient test model
        based on a combination of a regular attribute and multiple EAV attributes.
        """
        self.init_data()

        # Use the filter method with 3 EAV attribute conditions
        patients = Patient.objects.filter(
            name="Anne",
            eav__age=3,
            eav__illness="cold",
            eav__fever="no",
        )

        # Assert that the expected patient is returned
        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0].name, "Anne")
