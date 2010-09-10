from django.db import models


class Patient(models.Model):
    class Meta:
        app_label = 'eav_ng'

    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name
        
