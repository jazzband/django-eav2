"""Where an entity gets its attributes (its "schema") from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.db.models import Model

    from eav.models import Attribute, Entity


class SchemaSource(Protocol):
    """Something that can load the attributes available to an entity."""

    def load(self) -> Mapping[str, Attribute]:
        """Return the attributes by slug, in display order."""
        raise NotImplementedError


class OwnSchema:
    """The attributes of a single entity, loaded once on first use."""

    def __init__(self, entity: Entity) -> None:
        """Remember the *entity* whose attributes are loaded."""
        self._entity = entity
        self._attributes: Mapping[str, Attribute] | None = None

    def load(self) -> Mapping[str, Attribute]:
        """Return the attributes by slug, querying only the first time."""
        if self._attributes is None:
            self._attributes = {
                attribute.slug: attribute
                for attribute in self._entity.get_all_attributes()
            }
        return self._attributes


class SharedSchema:
    """
    The attributes shared by all the entities of a queryset, loaded once.

    Only used when every entity of the model has the same attributes, see
    :meth:`eav.registry.EavConfig.shares_attributes`. Nothing is queried unless
    an entity reads an attribute.
    """

    def __init__(self, model_cls: type[Model]) -> None:
        """Remember the model whose attributes are loaded."""
        self._model_cls = model_cls
        self._attributes: Mapping[str, Attribute] | None = None

    def attach(self, instance: Model) -> None:
        """Make the entity of *instance* read its attributes from this schema."""
        getattr(instance, self._config_cls.eav_attr).use_schema(self)

    def load(self) -> Mapping[str, Attribute]:
        """Return the attributes by slug, querying only the first time."""
        if self._attributes is None:
            attributes = self._config_cls.get_attributes().order_by("display_order")
            self._attributes = {
                attribute.slug: attribute
                for attribute in attributes.select_related("enum_group")
            }
        return self._attributes

    @property
    def _config_cls(self) -> Any:
        """The EAV config of the model, looked up so this stays picklable."""
        return getattr(self._model_cls, "_eav_config_cls")  # noqa: B009


def shared_schema_for(model_cls: type[Model]) -> SharedSchema | None:
    """Return a schema to share between the entities of *model_cls*, if allowed."""
    config_cls = getattr(model_cls, "_eav_config_cls", None)

    if config_cls is None or config_cls.manager_only:
        return None

    return SharedSchema(model_cls) if config_cls.shares_attributes() else None
