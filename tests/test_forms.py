import sys

from django.contrib.admin.sites import AdminSite
from django.core.handlers.base import BaseHandler
from django.forms import ModelForm
from django.test import TestCase
from django.test.client import RequestFactory

import eav
from eav.admin import *
from eav.forms import BaseDynamicEntityForm
from eav.models import Attribute
from test_project.models import ExampleModel, M2MModel, Patient


class MockRequest(RequestFactory):
    def request(self, **request):
        "Construct a generic request object."
        request = RequestFactory.request(self, **request)
        handler = BaseHandler()
        handler.load_middleware()
        # BaseHandler_request_middleware is not set in Django2.0
        # and removed in Django2.1
        if sys.version_info[0] < 2:
            for middleware_method in handler._request_middleware:
                if middleware_method(request):
                    raise Exception(
                        "Couldn't create request mock object - "
                        "request middleware returned a response"
                    )
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
        fields = '__all__'


class M2MModelForm(ModelForm):
    class Meta:
        model = M2MModel
        fields = '__all__'


class Forms(TestCase):
    def setUp(self):
        eav.register(Patient)
        Attribute.objects.create(name='weight', datatype=Attribute.TYPE_FLOAT)
        Attribute.objects.create(name='color', datatype=Attribute.TYPE_TEXT)

        self.female = EnumValue.objects.create(value='Female')
        self.male = EnumValue.objects.create(value='Male')
        gender_group = EnumGroup.objects.create(name='Gender')
        gender_group.values.add(self.female, self.male)

        Attribute.objects.create(
            name='gender', datatype=Attribute.TYPE_ENUM, enum_group=gender_group
        )

        self.instance = Patient.objects.create(name='Jim Morrison')
        self.site = AdminSite()

    def test_fields(self):
        admin = BaseEntityAdmin(Patient, self.site)
        admin.form = BaseDynamicEntityForm
        view = admin.change_view(request, str(self.instance.pk))

        own_fields = 3
        adminform = view.context_data['adminform']

        self.assertEqual(
            len(adminform.form.fields), Attribute.objects.count() + own_fields
        )

    def test_valid_submit(self):
        self.instance.eav.color = 'Blue'
        form = PatientForm(self.instance.__dict__, instance=self.instance)
        jim = form.save()

        self.assertEqual(jim.eav.color, 'Blue')

    def test_invalid_submit(self):
        form = PatientForm(dict(color='Blue'), instance=self.instance)
        with self.assertRaises(ValueError):
            jim = form.save()

    def test_valid_enums(self):
        self.instance.eav.gender = self.female
        form = PatientForm(self.instance.__dict__, instance=self.instance)
        rose = form.save()

        self.assertEqual(rose.eav.gender, self.female)

    def test_m2m(self):
        m2mmodel = M2MModel.objects.create(name='name')
        model = ExampleModel.objects.create(name='name')
        form = M2MModelForm(dict(name='Lorem', models=[model.pk]), instance=m2mmodel)
        form.save()
        self.assertEqual(len(m2mmodel.models.all()), 1)
