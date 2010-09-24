#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
#
#    This software is derived from EAV-Django originally written and 
#    copyrighted by Andrey Mikhaylenko <http://pypi.python.org/pypi/eav-django>
#
#    This is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This software is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with EAV-Django.  If not, see <http://gnu.org/licenses/>.
from datetime import datetime, date

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

def validate_text(value):
    '''
    Validates text
    '''
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
