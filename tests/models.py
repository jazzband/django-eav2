from django.db import models
from eav.decorators import register_eav


class Patient(models.Model):
    name = models.CharField(max_length=12)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Encounter(models.Model):
    num = models.PositiveSmallIntegerField()
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)

    def __str__(self):
        return '%s: encounter num %d' % (self.patient, self.num)

    def __repr__(self):
        return self.name


@register_eav()
class ExampleModel(models.Model):
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name


@register_eav()
class M2MModel(models.Model):
    name = models.CharField(max_length=12)
    models = models.ManyToManyField(ExampleModel)

    def __unicode__(self):
        return self.name
