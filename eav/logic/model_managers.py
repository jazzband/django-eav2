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
    def get_by_natural_key(self, id, value, attribute):
        from eav.models import Attribute

        attribute = Attribute.objects.get(**attribute)
        return self.get(id=id, value=value, attribute=attribute)
