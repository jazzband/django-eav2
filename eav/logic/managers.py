from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.db import models

if TYPE_CHECKING:
    from eav.models import Attribute, EnumGroup, EnumValue, Value


class EnumValueManager(models.Manager["EnumValue"]):
    """
    Custom manager for `EnumValue` model.

    This manager adds utility methods specific to the `EnumValue` model.
    """

    def get_by_natural_key(self, choice: str) -> EnumValue:
        """
        Retrieve an EnumValue instance using its `value` as a natural key.

        Args:
            choice (str): The value of the EnumValue instance.

        Returns:
            EnumValue: The instance matching the provided value.
        """
        return self.get(value=choice)


class EnumGroupManager(models.Manager["EnumGroup"]):
    """
    Custom manager for `EnumGroup` model.

    This manager adds utility methods specific to the `EnumGroup` model.
    """

    def get_by_natural_key(self, name: str) -> EnumGroup:
        """
        Retrieve an EnumGroup instance using its `name` as a natural key.

        Args:
            name (str): The name of the EnumGroup instance.

        Returns:
            EnumGroup: The instance matching the provided name.
        """
        return self.get(name=name)


class AttributeManager(models.Manager["Attribute"]):
    """
    Custom manager for `Attribute` model.

    This manager adds utility methods specific to the `Attribute` model.
    """

    def get_by_natural_key(self, name: str, slug: str) -> Attribute:
        """
        Retrieve an Attribute instance using its `name` and `slug` as natural keys.

        Args:
            name (str): The name of the Attribute instance.
            slug (str): The slug of the Attribute instance.

        Returns:
            Attribute: The instance matching the provided name and slug.
        """
        return self.get(name=name, slug=slug)


class ValueManager(models.Manager["Value"]):
    """
    Custom manager for `Value` model.

    This manager adds utility methods specific to the `Value` model.
    """

    def get_by_natural_key(
        self,
        attribute: tuple[str, str],
        entity_id: int | None,
        entity_uuid: Any,
    ) -> Value:
        """
        Retrieve a Value instance using multiple natural keys.

        This method utilizes a combination of an `attribute` (defined by its
        name and slug), `entity_id`, and `entity_uuid` to retrieve a unique
        Value instance.

        Args:
            attribute (tuple): A tuple containing the name and slug of the
                Attribute instance.
            entity_id (int): The ID of the associated entity.
            entity_uuid (str): The UUID of the associated entity.

        Returns:
            Value: The instance matching the provided keys.
        """
        attribute_model = apps.get_model("eav", "Attribute")
        found = attribute_model.objects.get(name=attribute[0], slug=attribute[1])

        return self.get(
            attribute=found,
            entity_id=entity_id,
            entity_uuid=entity_uuid,
        )
