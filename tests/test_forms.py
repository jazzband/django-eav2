import pytest
from django.contrib.admin.sites import AdminSite
from django.core.handlers.base import BaseHandler
from django.forms import ModelForm
from django.test import TestCase
from django.test.client import RequestFactory

import eav
from eav.admin import BaseEntityAdmin
from eav.forms import BaseDynamicEntityForm
from eav.models import Attribute, EnumGroup, EnumValue
from test_project.models import ExampleModel, M2MModel, Patient


class MockRequest(RequestFactory):
    def request(self, **request):
        "Construct a generic request object."
        request = RequestFactory.request(self, **request)
        handler = BaseHandler()
        handler.load_middleware()

        return request


class MockSuperUser:
    def __init__(self):
        self.is_active = True
        self.is_staff = True

    def has_perm(self, perm):
        return True


request = MockRequest().request()
request.user = MockSuperUser()


class PatientForm(ModelForm):
    class Meta:
        model = Patient
        fields = ("name", "email", "example")


class PatientDynamicForm(BaseDynamicEntityForm):
    class Meta:
        model = Patient
        fields = ("name", "email", "example")


class M2MModelForm(ModelForm):
    class Meta:
        model = M2MModel
        fields = ("name", "models")


class Forms(TestCase):
    def setUp(self):
        eav.register(Patient)
        Attribute.objects.create(name="weight", datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name="color", datatype=Attribute.TYPE_TEXT)

        self.female = EnumValue.objects.create(value="Female")
        self.male = EnumValue.objects.create(value="Male")
        gender_group = EnumGroup.objects.create(name="Gender")
        gender_group.values.add(self.female, self.male)

        Attribute.objects.create(
            name="gender",
            datatype=Attribute.TYPE_ENUM,
            enum_group=gender_group,
        )

        self.instance = Patient.objects.create(name="Jim Morrison")

    def test_valid_submit(self):
        self.instance.eav.color = "Blue"
        form = PatientForm(self.instance.__dict__, instance=self.instance)
        jim = form.save()

        self.assertEqual(jim.eav.color, "Blue")

    def test_invalid_submit(self):
        form = PatientForm({"color": "Blue"}, instance=self.instance)
        with self.assertRaises(ValueError):
            form.save()

    def test_valid_enums(self):
        self.instance.eav.gender = self.female
        form = PatientForm(self.instance.__dict__, instance=self.instance)
        rose = form.save()

        self.assertEqual(rose.eav.gender, self.female)

    def test_m2m(self):
        m2mmodel = M2MModel.objects.create(name="name")
        model = ExampleModel.objects.create(name="name")
        form = M2MModelForm({"name": "Lorem", "models": [model.pk]}, instance=m2mmodel)
        form.save()
        self.assertEqual(len(m2mmodel.models.all()), 1)


@pytest.fixture
def patient() -> Patient:
    """Return an eav enabled Patient instance."""
    eav.register(Patient)
    return Patient.objects.create(name="Jim Morrison")


@pytest.fixture
def create_attributes() -> None:
    """Create some Attributes to use for testing."""
    Attribute.objects.create(name="weight", datatype=Attribute.TYPE_FLOAT)
    Attribute.objects.create(name="color", datatype=Attribute.TYPE_TEXT)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("csv_data", "separator"),
    [
        ("", ";"),
        ("justone", ","),
        ("one;two;three", ";"),
        ("alpha,beta,gamma", ","),
        (None, ","),
    ],
)
def test_csvdynamicform(patient, csv_data, separator) -> None:
    """Ensure that a TYPE_CSV field works correctly with forms."""
    Attribute.objects.create(name="csv", datatype=Attribute.TYPE_CSV)
    patient.eav.csv = csv_data
    patient.save()
    patient.refresh_from_db()

    form = PatientDynamicForm(
        patient.__dict__,
        instance=patient,
    )
    form.fields["csv"].separator = separator
    assert form.is_valid()
    jim = form.save()

    expected_result = str(csv_data).split(separator) if csv_data else []
    assert jim.eav.csv == expected_result


@pytest.mark.django_db
def test_csvdynamicform_empty(patient) -> None:
    """Test to ensure an instance with no eav values is correct."""
    form = PatientDynamicForm(
        patient.__dict__,
        instance=patient,
    )
    assert form.is_valid()
    assert form.save()


@pytest.mark.django_db
@pytest.mark.usefixtures("create_attributes")
@pytest.mark.parametrize("define_fieldsets", [True, False])
def test_entity_admin_form(patient, define_fieldsets):
    """Test the BaseEntityAdmin form setup and dynamic fieldsets handling."""
    admin = BaseEntityAdmin(Patient, AdminSite())
    admin.readonly_fields = ("email",)
    admin.form = BaseDynamicEntityForm
    expected_fieldsets = 2

    if define_fieldsets:
        # Use all fields in Patient model
        admin.fieldsets = (
            (None, {"fields": ["name", "example"]}),
            ("Contact Info", {"fields": ["email"]}),
        )
        expected_fieldsets = 3

    view = admin.change_view(request, str(patient.pk))

    adminform = view.context_data["adminform"]

    # Count the total fields in fieldsets
    total_fields = sum(
        len(fields_info["fields"]) for _, fields_info in adminform.fieldsets
    )

    # 3 for 'name', 'email', 'example'
    expected_fields_count = Attribute.objects.count() + 3

    assert total_fields == expected_fields_count

    # Ensure our fieldset count is correct
    assert len(adminform.fieldsets) == expected_fieldsets


@pytest.mark.django_db
def test_entity_admin_form_no_attributes(patient):
    """Test the BaseEntityAdmin form with no Attributes created."""
    admin = BaseEntityAdmin(Patient, AdminSite())
    admin.readonly_fields = ("email",)
    admin.form = BaseDynamicEntityForm

    # Only fields defined in Patient model
    expected_fields = 3

    view = admin.change_view(request, str(patient.pk))

    adminform = view.context_data["adminform"]

    # Count the total fields in fieldsets
    total_fields = sum(
        len(fields_info["fields"]) for _, fields_info in adminform.fieldsets
    )

    # 3 for 'name', 'email', 'example'
    assert total_fields == expected_fields


@pytest.mark.django_db
def test_dynamic_form_renders_enum_choices():
    """
    Test that enum choices render correctly in BaseDynamicEntityForm.

    This test verifies the fix for issue #648 where enum choices weren't
    rendering correctly in Django 4.2.17 due to QuerySet unpacking issues.
    """
    # Setup
    eav.register(Patient)

    # Create enum values and group
    female = EnumValue.objects.create(value="Female")
    male = EnumValue.objects.create(value="Male")
    gender_group = EnumGroup.objects.create(name="Gender")
    gender_group.values.add(female, male)

    Attribute.objects.create(
        name="gender",
        datatype=Attribute.TYPE_ENUM,
        enum_group=gender_group,
    )

    # Create a patient
    patient = Patient.objects.create(name="Test Patient")

    # Initialize the dynamic form
    form = PatientDynamicForm(instance=patient)

    # Test rendering - should not raise any exceptions
    rendered_form = form.as_p()

    # Verify the form rendered and contains the enum choices
    assert 'name="gender"' in rendered_form
    assert f'value="{female.pk}">{female.value}' in rendered_form
    assert f'value="{male.pk}">{male.value}' in rendered_form
