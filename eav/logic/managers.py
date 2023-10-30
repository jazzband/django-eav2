from django.db import models


class EnumValueManager(models.Manager):
    """
    Custom manager for `EnumValue` model.

    This manager adds utility methods specific to the `EnumValue` model.
    """

    def get_by_natural_key(self, value):
        """
        Retrieves an EnumValue instance using its `value` as a natural key.

        Args:
            value (str): The value of the EnumValue instance.

        Returns:
            EnumValue: The instance matching the provided value.
        """
        return self.get(value=value)


class EnumGroupManager(models.Manager):
    """
    Custom manager for `EnumGroup` model.

    This manager adds utility methods specific to the `EnumGroup` model.
    """

    def get_by_natural_key(self, name):
        """
        Retrieves an EnumGroup instance using its `name` as a natural key.

        Args:
            name (str): The name of the EnumGroup instance.

        Returns:
            EnumGroup: The instance matching the provided name.
        """
        return self.get(name=name)


class AttributeManager(models.Manager):
    """
    Custom manager for `Attribute` model.

    This manager adds utility methods specific to the `Attribute` model.
    """

    def get_by_natural_key(self, name, slug):
        """
        Retrieves an Attribute instance using its `name` and `slug` as natural keys.

        Args:
            name (str): The name of the Attribute instance.
            slug (str): The slug of the Attribute instance.

        Returns:
            Attribute: The instance matching the provided name and slug.
        """
        return self.get(name=name, slug=slug)


class ValueManager(models.Manager):
    """
    Custom manager for `Value` model.

    This manager adds utility methods specific to the `Value` model.
    """

    def get_by_natural_key(self, attribute, entity_id, entity_uuid):
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
        from eav.models import Attribute

        attribute = Attribute.objects.get(name=attribute[0], slug=attribute[1])

        return self.get(
            attribute=attribute,
            entity_id=entity_id,
            entity_uuid=entity_uuid,
        )
