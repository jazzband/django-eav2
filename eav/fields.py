import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from eav.forms import CSVFormField


class EavSlugField(models.SlugField):
    """
    The slug field used by :class:`~eav.models.Attribute`
    """

    def validate(self, value, instance):
        """
        Slugs are used to convert the Python attribute name to a database
        lookup and vice versa. We need it to be a valid Python identifier. We
        don't want it to start with a '_', underscore will be used in
        variables we don't want to be saved in the database.
        """
        super(EavSlugField, self).validate(value, instance)
        slug_regex = r'[a-z][a-z0-9_]*'

        if not re.match(slug_regex, value):
            raise ValidationError(
                _(
                    'Must be all lower case, start with a letter, and contain '
                    'only letters, numbers, or underscores.'
                )
            )

    @staticmethod
    def create_slug_from_name(name):
        """Creates a slug based on the name."""
        name = name.strip().lower()

        # Change spaces to underscores.
        name = '_'.join(name.split())

        # Remove non alphanumeric characters.
        return re.sub('[^\w]', '', name)


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
