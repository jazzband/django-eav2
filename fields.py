import uuid
import re

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError


class EavSlugField(models.SlugField):
        
    def validate(self, value, instance):
        super(EavSlugField, self).validate(value, instance)
        slug_regex = r'[a-z]+[a-z0-9_]*'
        if not re.match(slug_regex, value):
            raise ValidationError(_(u"Must be all lower case, "\
                                    u"not start with a number, and contain "\
                                    u"only letters, numbers, or underscores."))

    @staticmethod
    def create_slug_from_name(name):
        '''
        Creates a slug based on the name
        '''
        name = name.strip().lower()

        # Change spaces to underscores
        name = re.sub('\s+', '_', name)

        # Remove non alphanumeric characters
        return re.sub('[^\w]', '', name)


class EavDatatypeField(models.CharField):

    def validate(self, value, instance):
        super(EavDatatypeField, self).validate(value, instance)
        from .models import EavAttribute
        if not instance.pk:
            return
        if value != EavAttribute.objects.get(pk=instance.pk).datatype:
            raise ValidationError(_(u"You cannot change the datatype of an "
                                    u"existing attribute."))
