"""
This module contains the custom manager used by entities registered with eav.
"""

from django.db import models

from .queryset import EavQuerySet


class EntityManager(models.Manager):
    """
    Our custom manager, overrides ``models.Manager``.
    """
    _queryset_class = EavQuerySet

    def create(self, **kwargs):
        """
        Parse eav attributes out of *kwargs*, then try to create and save
        the object, then assign and save it's eav attributes.
        """
        config_cls = getattr(self.model, '_eav_config_cls', None)

        if not config_cls or config_cls.manager_only:
            return super(EntityManager, self).create(**kwargs)

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
        """
        Reproduces the behavior of get_or_create, eav friendly.
        """
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            return self.create(**kwargs), True
