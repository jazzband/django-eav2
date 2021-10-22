import sys
import uuid

if sys.version_info >= (3, 8):
    from typing import Final, final
else:
    from typing_extensions import Final, final

from django.db import models

from eav.decorators import register_eav
from eav.models import EAVModelMeta

#: Constants
MAX_CHARFIELD_LEN: Final = 254


class TestBase(models.Model):
    """Base class for test models."""

    class Meta(object):
        """Define common options."""

        app_label = 'test_project'
        abstract = True


@final
@register_eav()
class Doctor(TestBase):
    """Test model using UUID as primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)


@final
class Patient(TestBase):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)
    email = models.EmailField(max_length=MAX_CHARFIELD_LEN, blank=True)
    example = models.ForeignKey(
        'ExampleModel',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
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
@final
class ExampleModel(TestBase):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)

    def __unicode__(self):
        return self.name


@register_eav()
@final
class M2MModel(TestBase):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)
    models = models.ManyToManyField(ExampleModel)

    def __unicode__(self):
        return self.name


@final
class ExampleMetaclassModel(TestBase, metaclass=EAVModelMeta):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)

    def __str__(self):
        return self.name


@final
class RegisterTestModel(TestBase, metaclass=EAVModelMeta):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)

    def __str__(self):
        return self.name
