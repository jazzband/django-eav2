from django.db import models


class EnumValueManager(models.Manager):
    def get_by_natural_key(self, value):
        return self.get(value=value)


class EnumGroupManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class AttributeManager(models.Manager):
    def get_by_natural_key(self, name, slug):
        return self.get(name=name, slug=slug)


class ValueManager(models.Manager):
    def get_by_natural_key(self, attribute, entity_id, entity_uuid):
        from eav.models import Attribute

        attribute = Attribute.objects.get(name=attribute[0], slug=attribute[1])

        return self.get(
            attribute=attribute, entity_id=entity_id, entity_uuid=entity_uuid
        )
