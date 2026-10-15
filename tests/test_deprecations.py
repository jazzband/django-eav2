from __future__ import annotations

import contextlib
import subprocess
import sys
import warnings

import pytest
from django.db.utils import NotSupportedError

import eav
from eav.exceptions import RemovedInEav3Warning
from eav.logic.bulk import BulkValueWriter
from eav.models import Attribute, EnumGroup, EnumValue
from test_project.models import Patient

pytestmark = pytest.mark.django_db

_DEPRECATED = (
    (Attribute.TYPE_JSON, "JSONField", {"a": 1}),
    (Attribute.TYPE_CSV, "related model", "a;b"),
    (Attribute.TYPE_OBJECT, "ManyToManyField", None),
)


@pytest.fixture(autouse=True)
def _register() -> None:
    eav.register(Patient)


@pytest.mark.parametrize(("datatype", "alternative", "_assigned"), _DEPRECATED)
def test_creating_a_deprecated_attribute_warns(datatype, alternative, _assigned):
    pattern = rf"'{datatype}' datatype of attribute 'legacy'.*3\.0.*{alternative}"

    with pytest.warns(RemovedInEav3Warning, match=pattern):
        Attribute.objects.create(name="legacy", datatype=datatype)


def test_the_warning_points_at_the_calling_code() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Attribute.objects.create(name="tags", datatype=Attribute.TYPE_CSV)
        Patient.objects.create(name="Joe", eav__tags="a;b")

        assert [warning.filename for warning in caught] == [__file__, __file__]


@pytest.mark.parametrize(("datatype", "_alternative", "assigned"), _DEPRECATED)
def test_storing_a_value_of_a_deprecated_datatype_warns(
    datatype,
    _alternative,
    assigned,
) -> None:
    with pytest.warns(RemovedInEav3Warning):
        Attribute.objects.create(name="legacy", datatype=datatype)

    if datatype == Attribute.TYPE_OBJECT:
        assigned = Patient.objects.create(name="Owner")

    with pytest.warns(RemovedInEav3Warning, match=f"'{datatype}'"):
        Patient.objects.create(name="Joe", eav__legacy=assigned)


def test_bulk_writes_of_a_deprecated_datatype_warn() -> None:
    with pytest.warns(RemovedInEav3Warning):
        Attribute.objects.create(name="tags", datatype=Attribute.TYPE_CSV)

    patient = Patient(name="Joe")
    patient.eav.tags = "a;b"

    # MySQL cannot return integer keys, so it raises after the warning.
    with (
        pytest.warns(RemovedInEav3Warning, match="'csv'"),
        contextlib.suppress(NotSupportedError),
    ):
        Patient.objects.bulk_create([patient])


def test_the_bulk_warning_comes_before_the_primary_key_check() -> None:
    with pytest.warns(RemovedInEav3Warning):
        Attribute.objects.create(name="tags", datatype=Attribute.TYPE_CSV)

    unsaved = Patient(name="Joe")
    unsaved.eav.tags = "a;b"
    writer = BulkValueWriter(Patient)

    with (
        pytest.warns(RemovedInEav3Warning, match="'csv'"),
        pytest.raises(NotSupportedError, match="Primary keys are needed"),
    ):
        writer.write([unsaved])


def test_other_datatypes_do_not_warn() -> None:
    group = EnumGroup.objects.create(name="Sizes")
    group.values.add(EnumValue.objects.create(value="big"))
    attributes = {
        Attribute.TYPE_TEXT: "text",
        Attribute.TYPE_INT: 1,
        Attribute.TYPE_FLOAT: 1.5,
        Attribute.TYPE_BOOLEAN: True,
        Attribute.TYPE_ENUM: "big",
    }

    with warnings.catch_warnings():
        warnings.simplefilter("error", RemovedInEav3Warning)

        for datatype, assigned in attributes.items():
            Attribute.objects.create(
                name=f"current {datatype}",
                datatype=datatype,
                enum_group=group if datatype == Attribute.TYPE_ENUM else None,
            )
            Patient.objects.create(
                name="Joe",
                **{f"eav__current_{datatype}": assigned},
            )


def test_python_shows_the_warning_by_default() -> None:
    script = """
import warnings
from eav.exceptions import RemovedInEav3Warning
warnings.warn('shown', RemovedInEav3Warning)
"""

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        cwd=".",
        env={"DJANGO_SETTINGS_MODULE": "test_project.settings", "PATH": ""},
    )

    assert b"RemovedInEav3Warning: shown" in result.stderr
