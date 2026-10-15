"""This module contains forms used for admin integration."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, ClassVar, cast

from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from eav.widgets import CSVWidget

if TYPE_CHECKING:
    from collections.abc import Mapping

    from eav.models import Attribute, Entity, EnumGroup


_FieldClasses = dict[str, type[forms.Field]]

#: Choices that come before the real ones of an enum attribute.
_BLANK_CHOICES = (("", ""), ("-----", "-----"))


class CSVFormField(forms.Field):
    """A form field for a list of values joined by a separator."""

    message = _("Enter comma-separated-values. eg: one;two;three.")
    code = "invalid"
    widget = CSVWidget
    default_separator = ";"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create the field, splitting its text on the ``separator`` argument."""
        kwargs.pop("max_length", None)
        self.separator = kwargs.pop("separator", self.default_separator)
        super().__init__(*args, **kwargs)

    def to_python(self, value: str | None) -> list[str]:
        """Split the text into a list of stripped values."""
        if not value:
            return []
        return [part.strip() for part in value.split(self.separator) if part]

    def validate(self, value: Any) -> None:
        """Require the cleaned value to be a list."""
        super().validate(value)

        if not isinstance(value, list):
            raise ValidationError(self.message, code=self.code)


class BaseDynamicEntityForm(forms.ModelForm):  # type: ignore[type-arg]
    """``ModelForm`` for an entity with support for EAV attributes.

    Form fields are created on the fly depending on the schema defined for the
    given entity instance. If no schema is defined (i.e. the entity instance has
    not been saved yet), only static fields are used. However, on form
    validation the schema will be retrieved and EAV fields dynamically added to
    the form, so when the validation is actually done, all EAV fields are present
    in it (unless Rubric is not defined).

    Mapping between attribute types and field classes is as follows:

    =====  =============
    Type      Field
    =====  =============
    text   CharField
    float  FloatField
    int    IntegerField
    date   SplitDateTimeField
    bool   BooleanField
    enum   ChoiceField
    json   JSONField
    csv    CSVField
    =====  =============
    """

    FIELD_CLASSES: ClassVar[_FieldClasses] = {
        "text": forms.CharField,
        "float": forms.FloatField,
        "int": forms.IntegerField,
        "date": forms.SplitDateTimeField,
        "bool": forms.BooleanField,
        "enum": forms.ChoiceField,
        "json": forms.JSONField,
        "csv": CSVFormField,
    }

    entity: Entity

    def __init__(
        self,
        data: Mapping[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Create the form and add a field for each attribute of the entity."""
        super().__init__(data, *args, **kwargs)
        config_cls = self.instance._eav_config_cls  # noqa: SLF001
        self.entity = getattr(self.instance, config_cls.eav_attr)
        self._build_dynamic_fields()

    def save(self, commit: bool = True) -> Any:  # noqa: FBT001, FBT002
        """Save the cleaned data into the instance and its EAV attributes.

        Returns ``instance``.
        """
        if self.errors:
            raise ValueError(
                _(
                    "The %s could not be saved because the data didn't validate.",
                )
                % self.instance._meta.object_name,  # noqa: SLF001
            )

        # Create entity instance, don't save yet.
        instance = super().save(commit=False)

        # Assign attributes.
        for attribute in self.entity.get_all_attributes():
            submitted = self.cleaned_data.get(attribute.slug)

            if attribute.datatype == attribute.TYPE_ENUM:
                group = cast("EnumGroup", attribute.enum_group)
                submitted = group.values.get(pk=submitted) if submitted else None

            setattr(self.entity, attribute.slug, submitted)

        # Save entity and its attributes.
        if commit:
            instance.save()
            self._save_m2m()  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

        return instance

    def _build_dynamic_fields(self) -> None:
        """Replace the form's fields with the static ones plus one per attribute."""
        self.fields = deepcopy(self.base_fields)

        for attribute in self.entity.get_all_attributes():
            current = getattr(self.entity, attribute.slug)
            field = self._build_field(attribute, current)

            if field is None:
                continue

            self.fields[attribute.slug] = field

            # Fill initial data (if attribute was already defined).
            if current and attribute.datatype != attribute.TYPE_ENUM:
                self.initial[attribute.slug] = current

    def _build_field(self, attribute: Attribute, current: Any) -> forms.Field | None:
        """Build the form field for *attribute*, or ``None`` if it has none."""
        if attribute.datatype == attribute.TYPE_OBJECT:
            return None

        defaults: dict[str, Any] = {
            "label": attribute.name.capitalize(),
            "required": attribute.required,
            "help_text": attribute.help_text,
            "validators": attribute.get_validators(),
        }

        if attribute.datatype == attribute.TYPE_ENUM:
            choices = [
                (item.pk, item.value) for item in attribute.enum_choices.values()
            ]
            defaults["choices"] = [*_BLANK_CHOICES, *choices]

            if current:
                defaults["initial"] = current.pk
        elif attribute.datatype == attribute.TYPE_DATE:
            defaults["widget"] = AdminSplitDateTime

        return self.FIELD_CLASSES[attribute.datatype](**defaults)
