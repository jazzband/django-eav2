from django.db import models
from eav.models import EAVModelMeta


class ExampleMetaclassModel(models.Model):
    __metaclass__ = EAVModelMeta
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name


class RegisterTestModel(models.Model):
    __metaclass__ = EAVModelMeta
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name
