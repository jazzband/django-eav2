from django.db import models
from eav.decorators import register_eav
from eav.models import EAVModelMeta


class ExampleMetaclassModel(models.Model, metaclass=EAVModelMeta):
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name


class RegisterTestModel(models.Model, metaclass=EAVModelMeta):
    name = models.CharField(max_length=12)

    def __unicode__(self):
        return self.name
