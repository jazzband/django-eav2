"""This module contains the custom manager used by entities registered with eav."""

from django.db import models

from eav.queryset import EavQuerySet


class EntityManager(models.Manager):
    """Our custom manager, overrides ``models.Manager``."""

    _queryset_class = EavQuerySet

    def create(self, **kwargs):
        """Create and save an object, together with its EAV attributes.

        EAV attributes are parsed out of *kwargs* first, then assigned and saved after
        the object itself.
        """
        config_cls = getattr(self.model, "_eav_config_cls", None)

        if not config_cls or config_cls.manager_only:
            return super().create(**kwargs)

        prefix = f"{config_cls.eav_attr}__"
        new_kwargs = {}
        eav_kwargs = {}

        for key, value in kwargs.items():
            if key.startswith(prefix):
                eav_kwargs.update({key[len(prefix) :]: value})
            else:
                new_kwargs.update({key: value})

        obj = self.model(**new_kwargs)
        obj_eav = getattr(obj, config_cls.eav_attr)

        for key, value in eav_kwargs.items():
            setattr(obj_eav, key, value)

        obj.save()
        return obj

    def get_or_create(self, defaults=None, **kwargs):
        """Reproduces the behavior of get_or_create, eav friendly."""
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            if defaults:
                kwargs = {**kwargs, **defaults}
            return self.create(**kwargs), True
