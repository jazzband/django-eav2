from __future__ import annotations

import pytest
from django.contrib.admin import StackedInline
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory

import eav
from eav.admin import BaseEntityInline
from test_project.models import Encounter, Patient

pytestmark = pytest.mark.django_db


class EncounterInline(BaseEntityInline, StackedInline):
    model = Encounter


@pytest.fixture(autouse=True)
def _register_models() -> None:
    eav.register(Patient)
    eav.register(Encounter)


def test_inline_builds_fieldsets_from_the_form() -> None:
    inline = EncounterInline(Patient, AdminSite())
    request = RequestFactory().post("/")
    request.user = User.objects.create_superuser("admin")

    fieldsets = inline.get_fieldsets(request, obj=Patient.objects.create(name="Joe"))

    assert [
        (title, {"fields": [name for name in options["fields"] if name != "id"]})
        for title, options in fieldsets
    ] == [(None, {"fields": ["num", "patient"]})]


def test_inline_uses_declared_fieldsets() -> None:
    inline = EncounterInline(Patient, AdminSite())
    inline.fieldsets = [(None, {"fields": ["num"]})]

    assert inline.get_fieldsets(RequestFactory().post("/")) == inline.fieldsets
