#!/usr/bin/env python
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
********
managers
********
Contains the custom manager used by entities registered with eav.

Functions and Classes
---------------------
'''
from django.db import models

from .queryset import EavQuerySet


class EntityManager(models.Manager):
    '''
    Our custom manager, overriding ``models.Manager``
    '''
    _queryset_class = EavQuerySet

    def create(self, **kwargs):
        '''
        Parse eav attributes out of *kwargs*, then try to create and save
        the object, then assign and save it's eav attributes.
        '''
        config_cls = getattr(self.model, '_eav_config_cls', None)

        if not config_cls or config_cls.manager_only:
            return super(EntityManager, self).create(**kwargs)

        #attributes = config_cls.get_attributes()
        prefix = '%s__' % config_cls.eav_attr

        new_kwargs = {}
        eav_kwargs = {}
        for key, value in kwargs.items():
            if key.startswith(prefix):
                eav_kwargs.update({key[len(prefix):]: value})
            else:
                new_kwargs.update({key: value})

        obj = self.model(**new_kwargs)
        obj_eav = getattr(obj, config_cls.eav_attr)
        for key, value in eav_kwargs.items():
            setattr(obj_eav, key, value)
        obj.save()
        return obj

    def get_or_create(self, **kwargs):
        '''
        Reproduces the behavior of get_or_create, eav friendly.
        '''
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            return self.create(**kwargs), True
