from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from eav.forms import CSVFormField


class EavDatatypeField(models.CharField):
    """
    The datatype field used by :class:`~eav.models.Attribute`.
    """

    def validate(self, value, instance):
        """
        Raise ``ValidationError`` if they try to change the datatype of an
        :class:`~eav.models.Attribute` that is already used by
        :class:`~eav.models.Value` objects.
        """
        super(EavDatatypeField, self).validate(value, instance)

        if not instance.pk:
            return

        # added
        if not type(instance).objects.filter(pk=instance.pk).exists():
            return

        if type(instance).objects.get(pk=instance.pk).datatype == instance.datatype:
            return

        if instance.value_set.count():
            raise ValidationError(
                _(
                    'You cannot change the datatype of an attribute that is already in use.'
                )
            )


class CSVField(models.TextField):  # (models.Field):
    description = _("A Comma-Separated-Value field.")
    default_separator = ";"

    def __init__(self, separator=";", *args, **kwargs):
        self.separator = separator
        kwargs.setdefault('default', "")
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.separator != self.default_separator:
            kwargs['separator'] = self.separator
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {'form_class': CSVFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return []
        return value.split(self.separator)

    def to_python(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return value.split(self.separator)

    def get_prep_value(self, value):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            return self.separator.join(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)
