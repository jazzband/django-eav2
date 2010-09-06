from django.db import models

from eav_ng.models import EavEntity, EavAttribute
from eav_ng.utils import EavRegistry

# Create your models here.
class Patient(models.Model):
    class Meta:
        app_label = 'eav_ng'


    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name
