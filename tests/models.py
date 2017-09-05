from django.db import models
from eav.decorators import register_eav


class Patient(models.Model):
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name

class Encounter(models.Model):
    num = models.PositiveSmallIntegerField()
    patient = models.ForeignKey(Patient)

    def __unicode__(self):
        return '%s: encounter num %d' % (self.patient, self.num)

@register_eav()
class ExampleModel(models.Model):
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name
