"""This module contains forms used for admin integration."""

from __future__ import annotations

from copy import deepcopy
from typing import ClassVar

from django.contrib.admin.widgets import AdminSplitDateTime
from django.core.exceptions import ValidationError
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    Field,
    FloatField,
    IntegerField,
    JSONField,
    ModelForm,
    SplitDateTimeField,
)
from django.utils.translation import gettext_lazy as _

from eav.widgets import CSVWidget


class CSVFormField(Field):
    message = _("Enter comma-separated-values. eg: one;two;three.")
    code = "invalid"
    widget = CSVWidget
    default_separator = ";"

    def __init__(self, *args, **kwargs):
        kwargs.pop("max_length", None)
        self.separator = kwargs.pop("separator", self.default_separator)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return []
        return [v.strip() for v in value.split(self.separator) if v]

    def validate(self, field_value):
        super().validate(field_value)

        if not isinstance(field_value, list):
            raise ValidationError(self.message, code=self.code)


class BaseDynamicEntityForm(ModelForm):
    """
    ``ModelForm`` for entity with support for EAV attributes. Form fields are
    created on the fly depending on schema defined for given entity instance.
    If no schema is defined (i.e. the entity instance has not been saved yet),
    only static fields are used. However, on form validation the schema will be
    retrieved and EAV fields dynamically added to the form, so when the
    validation is actually done, all EAV fields are present in it (unless
    Rubric is not defined).

    Mapping between attribute types and field classes is as follows:

    =====  =============
    Type      Field
    =====  =============
    text   CharField
    float  IntegerField
    int    DateTimeField
    date   SplitDateTimeField
    bool   BooleanField
    enum   ChoiceField
    json   JSONField
    csv    CSVField
    =====  =============
    """

    FIELD_CLASSES: ClassVar[dict[str, Field]] = {
        "text": CharField,
        "float": FloatField,
        "int": IntegerField,
        "date": SplitDateTimeField,
        "bool": BooleanField,
        "enum": ChoiceField,
        "json": JSONField,
        "csv": CSVFormField,
    }

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        config_cls = self.instance._eav_config_cls  # noqa: SLF001
        self.entity = getattr(self.instance, config_cls.eav_attr)
        self._build_dynamic_fields()

    def _build_dynamic_fields(self):
        # Reset form fields.
        self.fields = deepcopy(self.base_fields)

        for attribute in self.entity.get_all_attributes():
            value = getattr(self.entity, attribute.slug)

            defaults = {
                "label": attribute.name.capitalize(),
                "required": attribute.required,
                "help_text": attribute.help_text,
                "validators": attribute.get_validators(),
            }

            datatype = attribute.datatype

            if datatype == attribute.TYPE_ENUM:
                values = attribute.get_choices().values_list("id", "value")
                choices = [("", ""), ("-----", "-----"), *list(values)]
                defaults.update({"choices": choices})

                if value:
                    defaults.update({"initial": value.pk})

            elif datatype == attribute.TYPE_DATE:
                defaults.update({"widget": AdminSplitDateTime})
            elif datatype == attribute.TYPE_OBJECT:
                continue

            MappedField = self.FIELD_CLASSES[datatype]  # noqa: N806
            self.fields[attribute.slug] = MappedField(**defaults)

            # Fill initial data (if attribute was already defined).
            if value and datatype != attribute.TYPE_ENUM:
                self.initial[attribute.slug] = value

    def save(self, *, commit=True):
        """
        Saves this ``form``'s cleaned_data into model instance
        ``self.instance`` and related EAV attributes. Returns ``instance``.
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
            value = self.cleaned_data.get(attribute.slug)

            if attribute.datatype == attribute.TYPE_ENUM:
                value = attribute.enum_group.values.get(pk=value) if value else None

            setattr(self.entity, attribute.slug, value)

        # Save entity and its attributes.
        if commit:
            instance.save()
            self._save_m2m()

        return instance
