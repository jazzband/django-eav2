from datetime import datetime, date

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

def validate_text(value):
    if not (type(value) == unicode or type(value) == str):
        raise ValidationError(_(u"Must be str or unicode"))

def validate_float(value):
    try:
        float(value)
    except ValueError:
        raise ValidationError(_(u"Must be a float"))

def validate_int(value):
    try:
        int(value)
    except ValueError:
        raise ValidationError(_(u"Must be an integer"))

def validate_date(value):
    if not (isinstance(value, datetime) or isinstance(value, date)):
        raise ValidationError(_(u"Must be a date or datetime"))

def validate_bool(value):
    if not type(value) == bool:
        raise ValidationError(_(u"Must be a boolean"))

def validate_object(value):
    if not isinstance(value, models.Model):
        raise ValidationError(_(u"Must be a django model object instance"))
    if not value.pk:
        raise ValidationError(_(u"Model has not been saved yet"))

def validate_enum(value):
    from .models import EnumValue
    if not isinstance(value, EnumValue):
        raise ValidationError(_(u"Must be an EnumValue model object instance"))
    if not value.pk:
        raise ValidationError(_(u"EnumValue has not been saved yet"))
