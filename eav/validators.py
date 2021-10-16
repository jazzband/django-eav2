"""
This module contains a validator for each :class:`~eav.models.Attribute` datatype.

A validator is a callable that takes a value and raises a ``ValidationError``
if it doesn't meet some criteria (see `Django validators
<http://docs.djangoproject.com/en/dev/ref/validators/>`_).

These validators are called by the
:meth:`~eav.models.Attribute.validate_value` method in the
:class:`~eav.models.Attribute` model.
"""

import datetime
import json

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


def validate_text(value):
    """
    Raises ``ValidationError`` unless *value* type is ``str`` or ``unicode``
    """
    if not isinstance(value, str):
        raise ValidationError(_(u"Must be str or unicode"))


def validate_float(value):
    """
    Raises ``ValidationError`` unless *value* can be cast as a ``float``
    """
    try:
        float(value)
    except ValueError:
        raise ValidationError(_(u"Must be a float"))


def validate_int(value):
    """
    Raises ``ValidationError`` unless *value* can be cast as an ``int``
    """
    try:
        int(value)
    except ValueError:
        raise ValidationError(_(u"Must be an integer"))


def validate_date(value):
    """
    Raises ``ValidationError`` unless *value* is an instance of ``datetime``
    or ``date``
    """
    if not isinstance(value, datetime.datetime) and not isinstance(
        value, datetime.date
    ):
        raise ValidationError(_(u"Must be a date or datetime"))


def validate_bool(value):
    """
    Raises ``ValidationError`` unless *value* type is ``bool``
    """
    if not isinstance(value, bool):
        raise ValidationError(_(u"Must be a boolean"))


def validate_object(value):
    """
    Raises ``ValidationError`` unless *value* is a saved
    django model instance.
    """
    if not isinstance(value, models.Model):
        raise ValidationError(_(u"Must be a django model object instance"))

    if not value.pk:
        raise ValidationError(_(u"Model has not been saved yet"))


def validate_enum(value):
    """
    Raises ``ValidationError`` unless *value* is a saved
    :class:`~eav.models.EnumValue` model instance.
    """
    from eav.models import EnumValue

    if isinstance(value, EnumValue) and not value.pk:
        raise ValidationError(_(u"EnumValue has not been saved yet"))


def validate_json(value):
    """
    Raises ``ValidationError`` unless *value* can be cast as an ``json object`` (a dict)
    """
    try:
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict):
            raise ValidationError(_(u"Must be a JSON Serializable object"))
    except ValueError:
        raise ValidationError(_(u"Must be a JSON Serializable object"))


def validate_csv(value):
    """
    Raises ``ValidationError`` unless *value* is a c-s-v value.
    """
    if isinstance(value, str):
        value = value.split(";")
    if not isinstance(value, list):
        raise ValidationError(_(u"Must be Comma-Separated-Value."))
