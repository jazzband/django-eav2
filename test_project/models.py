import uuid
from typing import Final, final

from django.db import models

from eav.decorators import register_eav
from eav.managers import EntityManager
from eav.models import EAVModelMeta

#: Constants
MAX_CHARFIELD_LEN: Final = 254


class TestBase(models.Model):
    """Base class for test models."""

    class Meta:
        """Define common options."""

        app_label = "test_project"
        abstract = True


class DoctorManager(EntityManager):
    """
    Custom manager for the Doctor model.

    This manager extends the EntityManager and provides additional
    methods specific to the Doctor model, and is expected to be the
    default manager on the model.
    """

    def get_by_name(self, name: str) -> models.QuerySet:
        """Returns a QuerySet of doctors with the given name.

        Args:
            name (str): The name of the doctor to search for.

        Returns:
            models.QuerySet: A QuerySet of doctors with the specified name.
        """
        return self.filter(name=name)


class DoctorSubstringManager(models.Manager):
    """
    Custom manager for the Doctor model.

    This is a second manager used to ensure during testing that it's not replaced
    as the default manager after eav.register().
    """

    def get_by_name_contains(self, substring: str) -> models.QuerySet:
        """Returns a QuerySet of doctors whose names contain the given substring.

        Args:
            substring (str): The substring to search for in the doctor's name.

        Returns:
            models.QuerySet: A QuerySet of doctors whose names contain the
                specified substring.
        """
        return self.filter(name__icontains=substring)


@final
@register_eav()
class Doctor(TestBase):
    """Test model using UUID as primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)

    objects = DoctorManager()
    substrings = DoctorSubstringManager()

    def __str__(self):
        return self.name


@final
class Patient(TestBase):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)
    email = models.EmailField(max_length=MAX_CHARFIELD_LEN, blank=True)
    example = models.ForeignKey(
        "ExampleModel",
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
        return f"{self.patient}: encounter num {self.num}"

    def __repr__(self):
        return self.name


@register_eav()
@final
class ExampleModel(TestBase):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)

    def __str__(self):
        return self.name


@register_eav()
@final
class M2MModel(TestBase):
    name = models.CharField(max_length=MAX_CHARFIELD_LEN)
    models = models.ManyToManyField(ExampleModel)

    def __str__(self):
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
