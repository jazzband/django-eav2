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
'''
**********
validators
**********
This module contains a validator for each Attribute datatype.

A validator is a callable that takes a value and raises a ``ValidationError``
if it doesn’t meet some criteria. (see
`django validators <http://docs.djangoproject.com/en/dev/ref/validators/>`_)

These validators are called by the
:meth:`~eav.models.Attribute.validate_value` method in the
:class:`~eav.models.Attribute` model.

Functions
---------
'''

from django.utils import timezone
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError


def validate_text(value):
    '''
    Raises ``ValidationError`` unless *value* type is ``str`` or ``unicode``
    '''
    if not (type(value) == unicode or type(value) == str):
        raise ValidationError(_(u"Must be str or unicode"))


def validate_float(value):
    '''
    Raises ``ValidationError`` unless *value* can be cast as a ``float``
    '''
    try:
        float(value)
    except ValueError:
        raise ValidationError(_(u"Must be a float"))


def validate_int(value):
    '''
    Raises ``ValidationError`` unless *value* can be cast as an ``int``
    '''
    try:
        int(value)
    except ValueError:
        raise ValidationError(_(u"Must be an integer"))


def validate_date(value):
    '''
    Raises ``ValidationError`` unless *value* is an instance of ``datetime``
    or ``date``
    '''
    if not (isinstance(value, timezone.datetime) or isinstance(value, timezone.datetime.date)):
        raise ValidationError(_(u"Must be a date or datetime"))


def validate_bool(value):
    '''
    Raises ``ValidationError`` unless *value* type is ``bool``
    '''
    if not type(value) == bool:
        raise ValidationError(_(u"Must be a boolean"))


def validate_object(value):
    '''
    Raises ``ValidationError`` unless *value* is a saved
    django model instance.
    '''
    if not isinstance(value, models.Model):
        raise ValidationError(_(u"Must be a django model object instance"))
    if not value.pk:
        raise ValidationError(_(u"Model has not been saved yet"))


def validate_enum(value):
    '''
    Raises ``ValidationError`` unless *value* is a saved
    :class:`~eav.models.EnumValue` model instance.
    '''
    from .models import EnumValue
    if not isinstance(value, EnumValue):
        raise ValidationError(_(u"Must be an EnumValue model object instance"))
    if not value.pk:
        raise ValidationError(_(u"EnumValue has not been saved yet"))
