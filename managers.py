#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
#
#    This software is derrived from EAV-Django originally written and 
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

from functools import wraps

from django.db import models

from .models import EavAttribute, EavValue

def eav_filter(func):
    '''
    Decorator used to wrap filter and exlclude methods.  Passes args through
    expand_q_filters and kwargs through expand_eav_filter. Returns the
    called function (filter or exclude) .distinct()
    '''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        new_args = []
        for arg in args:
            if isinstance(arg, models.Q):
                # modify Q objects (warning: recursion ahead)
                arg = expand_q_filters(arg, self.model)
            new_args.append(arg)

        new_kwargs = {}
        for key, value in kwargs.items():
            # modify kwargs (warning: recursion ahead)
            new_key, new_value = expand_eav_filter(self.model, key, value)
            new_kwargs.update({new_key: new_value})

        return func(self, *new_args, **new_kwargs).distinct()
    return wrapper


def expand_q_filters(q, root_cls):
    '''
    Takes a Q object and a model class.
    Recursivley passes each filter / value in the Q object tree leaf nodes
    through expand_eav_filter
    '''
    new_children = []
    for qi in q.children:
        if type(qi) is tuple:
            # this child is a leaf node: in Q this is a 2-tuple of:
            # (filter parameter, value)
            key, value = expand_eav_filter(root_cls, *qi)
            new_children.append(models.Q(**{key: value}))
        else:
            # this child is another Q node: recursify!
            new_children.append(expand_q_filters(qi, root_cls))
    q.children = new_children
    return q


def expand_eav_filter(model_cls, key, value):
    '''
    Accepts a model class and a key, value.
    Recurisively replaces any eav filter with a subquery.

    For example:
        key = 'eav__height'
        value = 5
    Would return:
        key = 'eav_values__in'
        value = EavValues.objects.filter(value_int=5, attribute__slug='height')
    '''
    from .utils import EavRegistry
    fields = key.split('__')

    config_cls = EavRegistry.get_config_cls_for_model(model_cls)
    if len(fields) > 1 and config_cls and \
       fields[0] == config_cls.proxy_field_name:
        slug = fields[1]
        gr_name = config_cls.generic_relation_field_name
        datatype = EavAttribute.objects.get(slug=slug).datatype

        lookup = '__%s' % fields[2] if len(fields) > 2 else ''
        kwargs = {'value_%s%s' % (datatype, lookup): value,
                  'attribute__slug': slug}
        value = EavValue.objects.filter(**kwargs)

        return '%s__in' % gr_name, value

    try:
        field, m, direct, m2m = model_cls._meta.get_field_by_name(fields[0])
    except models.FieldDoesNotExist:
        return key, value

    if direct:
        return key, value
    else:
        sub_key = '__'.join(fields[1:])
        key, value = expand_eav_filter(field.model, sub_key, value)
        return '%s__%s' % (fields[0], key), value


class EntityManager(models.Manager):
    @eav_filter
    def filter(self, *args, **kwargs):
        return super(EntityManager, self).filter(*args, **kwargs)

    @eav_filter
    def exclude(self, *args, **kwargs):
        return super(EntityManager, self).exclude(*args, **kwargs)
