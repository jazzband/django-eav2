from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.widgets import Textarea

EMPTY_VALUES = validators.EMPTY_VALUES + ('[]',)


class CSVWidget(Textarea):
    is_hidden = False

    def prep_value(self, value):
        """Prepare value before effectively render widget"""
        if value in EMPTY_VALUES:
            return ""
        elif isinstance(value, str):
            return value
        elif isinstance(value, list):
            return ";".join(value)
        raise ValidationError('Invalid format.')

    def render(self, name, value, **kwargs):
        value = self.prep_value(value)
        return super().render(name, value, **kwargs)

    def value_from_datadict(self, data, files, name):
        """
        Return the value of this widget or None.

        Since we're only given the value of the entity name and the data dict
        contains the '_eav_config_cls' (which we don't have access to) as the
        key, we need to loop through each field checking if the eav attribute
        exists with the given 'name'.
        """
        widget_value = None
        for data_value in data:
            try:
                widget_value = getattr(data.get(data_value), name)
            except AttributeError:
                pass  # noqa: WPS420

        return widget_value
