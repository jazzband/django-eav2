"""Where an entity gets its attributes (its "schema") from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from eav.models import Attribute, Entity


class SchemaSource(Protocol):
    """Something that can load the attributes available to an entity."""

    def load(self) -> Mapping[str, Attribute]:
        """Return the attributes by slug, in display order."""
        raise NotImplementedError


class OwnSchema:
    """Loads the attributes of a single entity, once, on first use."""

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
