from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from eav.forms import CSVFormField

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django import forms


class EavDatatypeField(models.CharField):  # type: ignore[type-arg]
    """The datatype field used by :class:`~eav.models.Attribute`."""

    def validate(self, value: object, model_instance: Any) -> None:
        """Raise ``ValidationError`` if the datatype of a used attribute is changed.

        :class:`~eav.models.Attribute` objects that are already used by
        :class:`~eav.models.Value` objects cannot change their datatype.
        """
        super().validate(value, model_instance)

        if not model_instance.pk:
            return

        stored = (
            type(model_instance)
            .objects.filter(pk=model_instance.pk)
            .values_list("datatype", flat=True)
            .first()
        )

        if stored is None or stored == model_instance.datatype:
            return

        if model_instance.value_set.exists():
            raise ValidationError(
                _(
                    "You cannot change the datatype of an "
                    + "attribute that is already in use.",
                ),
            )


class CSVField(models.TextField):  # type: ignore[type-arg]
    """A text field holding a list of values joined by a separator."""

    description = _("A Comma-Separated-Value field.")
    default_separator = ";"

    def __init__(self, separator: str = ";", *args: Any, **kwargs: Any) -> None:
        """Create the field, splitting its text on *separator*."""
        self.separator = separator
        kwargs.setdefault("default", "")
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        """Describe the field for migrations, including a non-default separator."""
        name, path, args, kwargs = super().deconstruct()
        if self.separator != self.default_separator:
            kwargs["separator"] = self.separator
        return name, path, args, kwargs

    def formfield(
        self,
        form_class: type[forms.Field] | None = None,
        choices_form_class: type[forms.ChoiceField] | None = None,
        **kwargs: Any,
    ) -> forms.Field | None:
        """Use :class:`~eav.forms.CSVFormField` as the form field."""
        return super().formfield(
            form_class=form_class or CSVFormField,
            choices_form_class=choices_form_class,
            **kwargs,
        )

    def from_db_value(
        self,
        value: str | None,
        expression: Any,
        connection: Any,
    ) -> list[str]:
        """Convert the stored text to a list."""
        return self.to_python(value)

    def to_python(self, value: str | list[str] | None) -> list[str]:
        """Convert text, a list or ``None`` to a list."""
        if not value:
            return []
        if isinstance(value, list):
            return value
        return value.split(self.separator)

    def get_prep_value(self, value: Any) -> Any:
        """Convert a list to the text that is stored."""
        if not value:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return self.separator.join(value)
        return value

    def value_to_string(self, obj: Any) -> str:
        """Serialize the value as stored text."""
        value = self.value_from_object(obj)
        return str(self.get_prep_value(value))
