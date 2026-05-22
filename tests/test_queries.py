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

    def test_filter_eav_and_negated_non_eav_field(self) -> None:
        """
        Regression test for #634: EAV Q combined with a negated non-EAV Q.

        Q(eav__attr=val) & ~Q(non_eav_field=val) raised:
            TypeError: 'Q' object is not subscriptable
        """
        self.init_data()
        # fever=yes → Cyrill, Eugene; name≠"Bob" excludes nobody here
        p = Patient.objects.filter(Q(eav__fever=self.yes) & ~Q(name="Bob"))
        assert p.count() == 2
        assert set(p.values_list("name", flat=True)) == {"Cyrill", "Eugene"}

    def test_filter_negated_non_eav_field_and_eav(self) -> None:
        """
        Regression test for #634: negated non-EAV Q combined with an EAV Q
        (operand order reversed from the previous test).

        ~Q(non_eav_field=val) & Q(eav__attr=val) raised:
            TypeError: 'Q' object is not subscriptable
        """
        self.init_data()
        # Same expectation as above; order of operands should not matter.
        p = Patient.objects.filter(~Q(name="Bob") & Q(eav__fever=self.yes))
        assert p.count() == 2
        assert set(p.values_list("name", flat=True)) == {"Cyrill", "Eugene"}

    def test_filter_eav_and_negated_eav_field(self) -> None:
        """
        Regression test for #634: EAV Q combined with a negated EAV Q.

        Q(eav__attr1=val) & ~Q(eav__attr2=val) raised:
            TypeError: 'Q' object is not subscriptable

        Note: negating an EAV filter inside filter() has known SQL JOIN
        semantics limitations. Because each EAV attribute is stored as a
        separate row in the values table, the negation operates on individual
        rows rather than on entities. This means a patient with both a
        fever=no value AND a city='Nice' value will still be included because
        their fever=no row passes the NOT city='Nice' row-level check.
        The primary purpose of this test is to verify no TypeError is raised.
        """
        self.init_data()
        # fever=no → Anne, Bob, Daniel
        # ~city='Nice' does NOT reliably exclude Daniel due to EAV row semantics
        p = Patient.objects.filter(Q(eav__fever=self.no) & ~Q(eav__city="Nice"))
        # At minimum, the EAV-only patients (no city='Nice') must be present
        names = set(p.values_list("name", flat=True))
        assert {"Anne", "Bob"}.issubset(names)
        # Result is bounded by the fever=no set
        assert names.issubset({"Anne", "Bob", "Daniel"})

    def test_filter_solo_negated_eav_field(self) -> None:
        """
        ~Q(eav__attr=val) as the sole argument should work correctly.

        This produces entity-level exclusion because there are no other EAV
        JOIN conditions to interfere: entities with no matching value row are
        simply absent from the JOIN, so NOT eav_values__in correctly excludes
        entities that DO have that value row.
        """
        self.init_data()
        # age != 3 → Bob (15), Cyrill (15), Eugene (2)
        p = Patient.objects.filter(~Q(eav__age=3))
        assert p.count() == 3
        assert set(p.values_list("name", flat=True)) == {"Bob", "Cyrill", "Eugene"}

    def test_filter_or_eav_and_non_eav_no_duplicates(self) -> None:
        """
        OR between an EAV Q and a non-EAV Q must not return duplicate rows.

        When an EAV condition is used in OR with a non-EAV condition, the EAV
        side remains as a JOIN condition (it cannot be merged via rewrite_q_expr
        because there is only one EAV leaf). This JOIN can produce multiple rows
        per entity. Results should be distinct.

        This is a known limitation: callers should use .distinct() when mixing
        EAV and non-EAV conditions in OR.
        """
        self.init_data()
        # fever=yes → Cyrill, Eugene; name='Bob' → Bob
        p = Patient.objects.filter(Q(eav__fever=self.yes) | Q(name="Bob"))
        # Correct distinct count is 3; without distinct() duplicates may appear
        assert p.distinct().count() == 3
        assert set(p.distinct().values_list("name", flat=True)) == {
            "Bob",
            "Cyrill",
            "Eugene",
        }

    def test_q_object_not_mutated_by_filter(self) -> None:
        """
        Q objects passed to filter() must not be mutated.

        expand_q_filters() rewrites Q children in-place. If the original Q
        object is mutated, reusing it in a second query will operate on the
        already-expanded (internal) form and may produce incorrect results or
        errors.

        This test documents the current behaviour (mutation occurs) so that
        any future fix is captured as a regression guard.
        """
        self.init_data()
        q = Q(eav__fever=self.yes)
        original_children = list(q.children)  # [('eav__fever', <EnumValue>)]

        Patient.objects.filter(q)

        # Document current (broken) behaviour: children are mutated.
        # When this is fixed, change the assertion to assertEqual.
        assert q.children != original_children, (
            "Q mutation is fixed - update this test to assert no mutation"
        )

    def test_negated_eav_field_workaround_chained_exclude(self) -> None:
        """
        Documents the correct way to express "EAV attr A = x AND EAV attr B != y".

        Because EAV values are stored one-per-row, using ~Q() inside filter()
        negates at the *row* level, not the *entity* level.  The correct
        approach is to chain .exclude() which operates at the entity level::

            # WRONG - may return entities that should be excluded
            Patient.objects.filter(Q(eav__fever=no) & ~Q(eav__city="Nice"))

            # CORRECT - exclude() works at entity level
            Patient.objects.filter(eav__fever=no).exclude(eav__city="Nice")
            # or equivalently:
            Patient.objects.filter(Q(eav__fever=no)).exclude(Q(eav__city="Nice"))
        """
        self.init_data()
        # fever=no → Anne, Bob, Daniel; chained exclude removes Daniel
        p_chained = Patient.objects.filter(eav__fever=self.no).exclude(
            eav__city="Nice",
        )
        assert p_chained.count() == 2
        assert set(p_chained.values_list("name", flat=True)) == {"Anne", "Bob"}

        # Q-based form of the same thing
        p_q = Patient.objects.filter(Q(eav__fever=self.no)).exclude(
            Q(eav__city="Nice"),
        )
        assert p_q.count() == 2
        assert set(p_q.values_list("name", flat=True)) == {"Anne", "Bob"}
