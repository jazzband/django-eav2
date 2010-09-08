import uuid
import re

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError


class EavSlugField(models.SlugField):
        
    def validate(self, value, instance):
        """
            Slugs are used to convert the Python attribute name to a database
            lookup and vice versa. We need it to be a valid Python identifier.
            We don't want it to start with a '_', underscore will be used
            var variables we don't want to be saved in db.
        """
        super(EavSlugField, self).validate(value, instance)
        slug_regex = r'[a-z][a-z0-9_]*'
        if not re.match(slug_regex, value):
            raise ValidationError(_(u"Must be all lower case, "\
                                    u"starts with a letter, and contain "\
                                    u"only letters, numbers, or underscores."))

    @staticmethod
    def create_slug_from_name(name):
        '''
        Creates a slug based on the name
        '''
        name = name.strip().lower()

        # Change spaces to underscores
        name = '_'.join(name.split())

        # Remove non alphanumeric characters
        return re.sub('[^\w]', '', name)


class EavDatatypeField(models.SlugField):
    """
        This holds checks for the attributes datatypes.
    """

    def validate(self, value, instance):
        """
            We don't want them to be able to change the attribute type
            once it have been created.
        """
        super(EavDatatypeField, self).validate(value, instance)
        from .models import EavAttribute
        if not instance.pk:
            return
        if value != EavAttribute.objects.get(pk=instance.pk).datatype:
            raise ValidationError(_(u"You cannot change the datatype of an "
                                    u"existing attribute."))
