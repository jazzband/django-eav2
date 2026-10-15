"""This module contains the custom manager used by entities registered with eav."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from eav.queryset import EavQuerySet

if TYPE_CHECKING:
    from collections.abc import Mapping

_ModelT = TypeVar("_ModelT", bound=models.Model)


class EntityManager(models.Manager[_ModelT]):
    """A manager for EAV models that creates entities together with their attributes."""

    _queryset_class = EavQuerySet

    def create(self, **kwargs: Any) -> _ModelT:
        """Create and save an object, together with its EAV attributes.

        EAV attributes are parsed out of *kwargs* first, then assigned and saved after
        the object itself.
        """
        config_cls = getattr(self.model, "_eav_config_cls", None)

        if not config_cls or config_cls.manager_only:
            return super().create(**kwargs)

        prefix = f"{config_cls.eav_attr}__"
        eav_kwargs = {
            key.removeprefix(prefix): assigned
            for key, assigned in kwargs.items()
            if key.startswith(prefix)
        }
        model_kwargs = {
            key: assigned
            for key, assigned in kwargs.items()
            if not key.startswith(prefix)
        }

        instance = self.model(**model_kwargs)
        entity = getattr(instance, config_cls.eav_attr)

        for key, assigned in eav_kwargs.items():
            setattr(entity, key, assigned)

        instance.save()
        return instance

    def get_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[_ModelT, bool]:
        """Reproduces the behavior of get_or_create, eav friendly."""
        try:
            return self.get(**kwargs), False
        except ObjectDoesNotExist:
            if defaults:
                kwargs = {**kwargs, **defaults}
            return self.create(**kwargs), True
