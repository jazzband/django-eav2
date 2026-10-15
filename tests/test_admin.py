from __future__ import annotations

import pytest
from django.contrib.admin import ModelAdmin, StackedInline
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, override_settings
from django.urls import path

import eav
from eav.admin import BaseEntityAdmin, BaseEntityInline
from eav.forms import BaseDynamicEntityForm
from eav.models import Attribute
from test_project.models import Encounter, ExampleModel, Patient

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


class PatientForm(BaseDynamicEntityForm):
    class Meta:
        model = Patient
        fields = "__all__"


class EncounterForm(BaseDynamicEntityForm):
    class Meta:
        model = Encounter
        fields = "__all__"


class EncounterWithFormInline(BaseEntityInline, StackedInline):
    model = Encounter
    form = EncounterForm


class PatientAdmin(BaseEntityAdmin):
    form = PatientForm
    inlines = (EncounterInline,)


class PatientWithFormAdmin(BaseEntityAdmin):
    form = PatientForm
    inlines = (EncounterWithFormInline,)


class EncounterNumOnlyInline(BaseEntityInline, StackedInline):
    model = Encounter
    fields = ("num",)


class PatientNumOnlyAdmin(BaseEntityAdmin):
    form = PatientForm
    inlines = (EncounterNumOnlyInline,)


class PatientInline(BaseEntityInline, StackedInline):
    model = Patient


class ExampleAdmin(ModelAdmin):
    inlines = (PatientInline,)


plain_site = AdminSite(name="plain")
plain_site.register(Patient, PatientAdmin)
form_site = AdminSite(name="with_form")
form_site.register(Patient, PatientWithFormAdmin)
num_only_site = AdminSite(name="num_only")
num_only_site.register(Patient, PatientNumOnlyAdmin)
example_site = AdminSite(name="example")
example_site.register(ExampleModel, ExampleAdmin)

urlpatterns = [
    path("plain/", plain_site.urls),
    path("with-form/", form_site.urls),
    path("num-only/", num_only_site.urls),
    path("example/", example_site.urls),
]


@pytest.fixture
def admin_client(client):
    User.objects.create_superuser("admin", password="secret")  # noqa: S106
    client.login(username="admin", password="secret")  # noqa: S106
    return client


@pytest.mark.parametrize("prefix", ["plain", "with-form"])
@override_settings(ROOT_URLCONF=__name__)
def test_inline_shows_and_saves_the_attributes_of_its_entity(
    admin_client,
    prefix,
) -> None:
    Attribute.objects.create(name="note", datatype=Attribute.TYPE_TEXT)
    patient = Patient.objects.create(name="Ada")
    url = f"/{prefix}/test_project/patient/{patient.pk}/change/"

    page = admin_client.get(url)

    assert page.status_code == 200
    assert "id_encounter_set-0-note" in page.content.decode()

    saved = admin_client.post(
        url,
        {
            "name": "Ada",
            "email": "",
            "note": "parent note",
            "encounter_set-TOTAL_FORMS": "1",
            "encounter_set-INITIAL_FORMS": "0",
            "encounter_set-MIN_NUM_FORMS": "0",
            "encounter_set-MAX_NUM_FORMS": "1000",
            "encounter_set-0-num": "7",
            "encounter_set-0-note": "inline note",
            "encounter_set-0-patient": str(patient.pk),
        },
    )

    encounter = Encounter.objects.get(patient=patient)
    assert saved.status_code == 302
    assert encounter.eav.note == "inline note"
    assert Patient.objects.get(pk=patient.pk).eav.note == "parent note"


@pytest.mark.parametrize("prefix", ["plain", "with-form"])
@override_settings(ROOT_URLCONF=__name__)
def test_inline_on_the_add_page_and_for_an_existing_row(admin_client, prefix) -> None:
    Attribute.objects.create(name="note", datatype=Attribute.TYPE_TEXT)
    add = admin_client.get(f"/{prefix}/test_project/patient/add/")
    patient = Patient.objects.create(name="Ada")
    encounter = Encounter.objects.create(num=1, patient=patient, eav__note="first")
    change = admin_client.get(f"/{prefix}/test_project/patient/{patient.pk}/change/")

    assert add.status_code == 200
    assert "id_encounter_set-0-note" in add.content.decode()
    assert change.status_code == 200
    note = encounter.eav.note
    assert f'value="{note}"' in change.content.decode()


@override_settings(ROOT_URLCONF=__name__)
def test_inline_shows_only_the_declared_fields(admin_client) -> None:
    Attribute.objects.create(name="note", datatype=Attribute.TYPE_TEXT)
    patient = Patient.objects.create(name="Ada")

    page = admin_client.get(f"/num-only/test_project/patient/{patient.pk}/change/")

    html = page.content.decode()
    assert page.status_code == 200
    assert "id_encounter_set-0-num" in html
    assert "id_encounter_set-0-note" not in html


@override_settings(ROOT_URLCONF=__name__)
def test_inline_with_an_attribute_named_like_a_reverse_relation(admin_client) -> None:
    # ``Patient.encounter_set`` is queried as ``encounter``.
    Attribute.objects.create(name="encounter", datatype=Attribute.TYPE_TEXT)
    example = ExampleModel.objects.create(name="Example")

    page = admin_client.get(f"/example/test_project/examplemodel/{example.pk}/change/")

    assert page.status_code == 200
    assert "id_patient_set-0-encounter" in page.content.decode()
