from django.db import models

from eav.decorators import register_eav
from eav.models import EAVModelMeta


class TestBase(models.Model):
    """Base class for test models."""

    class Meta(object):
        """Define common options."""

        app_label = 'test_project'
        abstract = True


class Patient(TestBase):
    name = models.CharField(max_length=12)
    example = models.ForeignKey(
        'ExampleModel', null=True, blank=True, on_delete=models.PROTECT
    )

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Encounter(TestBase):
    num = models.PositiveSmallIntegerField()
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)

    def __str__(self):
        return '%s: encounter num %d' % (self.patient, self.num)

    def __repr__(self):
        return self.name


@register_eav()
class ExampleModel(TestBase):
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name


@register_eav()
class M2MModel(TestBase):
    name = models.CharField(max_length=12)
    models = models.ManyToManyField(ExampleModel)

    def __unicode__(self):
        return self.name


class ExampleMetaclassModel(TestBase, metaclass=EAVModelMeta):
    name = models.CharField(max_length=12)

    def __str__(self):
        return self.name


class RegisterTestModel(TestBase, metaclass=EAVModelMeta):
    name = models.CharField(max_length=12)

    def __str__(self):
        return self.name
