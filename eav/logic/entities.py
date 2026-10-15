"""Reaching the EAV helper of a model instance."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model

    from eav.models import Entity
    from eav.registry import EavConfig


def config_of(model: Model | type[Model]) -> type[EavConfig]:
    """Return the EAV config of a model class, or of the class of an instance."""
    model_cls = model if isinstance(model, type) else type(model)
    config_cls: type[EavConfig] = getattr(model_cls, "_eav_config_cls")  # noqa: B009
    return config_cls


def entity_of(instance: Model) -> Entity:
    """Return the EAV helper attached to *instance*."""
    entity: Entity = getattr(instance, config_of(instance).eav_attr)
    return entity
