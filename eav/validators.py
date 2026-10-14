"""
This module contains a validator for each :class:`~eav.models.Attribute` datatype.

A validator is a callable that takes a value and raises a ``ValidationError``
if it doesn't meet some criteria (see `Django validators
<https://docs.djangoproject.com/en/dev/ref/validators/>`_).

These validators are called by the
:meth:`~eav.models.Attribute.validate_value` method in the
:class:`~eav.models.Attribute` model.
"""

import datetime as dt
import json

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


def validate_text(candidate):
    """Raise ``ValidationError`` unless *candidate* type is ``str`` or ``unicode``."""
    if not isinstance(candidate, str):
        raise ValidationError(_("Must be str or unicode"))


def validate_float(candidate):
    """Raise ``ValidationError`` unless *candidate* can be cast as a ``float``."""
    try:
        float(candidate)
    except (TypeError, ValueError) as err:
        raise ValidationError(_("Must be a float")) from err


def validate_int(candidate):
    """Raise ``ValidationError`` unless *candidate* can be cast as an ``int``."""
    try:
        int(candidate)
    except (TypeError, ValueError) as err:
        raise ValidationError(_("Must be an integer")) from err


def validate_date(candidate):
    """Raise ``ValidationError`` unless *candidate* is a ``datetime`` or ``date``."""
    if not isinstance(candidate, dt.datetime) and not isinstance(
        candidate,
        dt.date,
    ):
        raise ValidationError(_("Must be a date or datetime"))


def validate_bool(candidate):
    """Raise ``ValidationError`` unless *candidate* type is ``bool``."""
    if not isinstance(candidate, bool):
        raise ValidationError(_("Must be a boolean"))


def validate_object(candidate):
    """Raise ``ValidationError`` unless *candidate* is a saved Django model instance."""
    if not isinstance(candidate, models.Model):
        raise ValidationError(_("Must be a django model object instance"))

    if candidate._state.adding:  # noqa: SLF001
        raise ValidationError(_("Model has not been saved yet"))


def validate_enum(candidate):
    """Raise ``ValidationError`` unless *candidate* is a saved ``EnumValue``."""
    enum_value_model = apps.get_model("eav", "EnumValue")

    if isinstance(candidate, enum_value_model) and candidate._state.adding:  # noqa: SLF001
        raise ValidationError(_("EnumValue has not been saved yet"))


def validate_json(candidate):
    """Raise ``ValidationError`` unless *candidate* is a dict or JSON text for one."""
    try:
        parsed = json.loads(candidate) if isinstance(candidate, str) else candidate
    except ValueError as err:
        raise ValidationError(_("Must be a JSON Serializable object")) from err

    if not isinstance(parsed, dict):
        raise ValidationError(_("Must be a JSON Serializable object"))


def validate_csv(candidate):
    """Raise ``ValidationError`` unless *candidate* is a c-s-v value."""
    if isinstance(candidate, str):
        candidate = candidate.split(";")
    if not isinstance(candidate, list):
        raise ValidationError(_("Must be Comma-Separated-Value."))
