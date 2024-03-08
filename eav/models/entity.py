from copy import copy

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _

from eav import register
from eav.exceptions import IllegalAssignmentException
from eav.logic.entity_pk import get_entity_pk_type

from .attribute import Attribute
from .enum_value import EnumValue
from .value import Value


class Entity:
    """Helper class that will be attached to entities registered with eav."""

    @staticmethod
    def pre_save_handler(sender, *args, **kwargs):
        """
        Pre save handler attached to self.instance.  Called before the
        model instance we are attached to is saved. This allows us to call
        :meth:`validate_attributes` before the entity is saved.
        """
        instance = kwargs['instance']
        entity = getattr(kwargs['instance'], instance._eav_config_cls.eav_attr)
        entity.validate_attributes()

    @staticmethod
    def post_save_handler(sender, *args, **kwargs):
        """
        Post save handler attached to self.instance.  Calls :meth:`save` when
        the model instance we are attached to is saved.
        """
        instance = kwargs['instance']
        entity = getattr(instance, instance._eav_config_cls.eav_attr)
        entity.save()

    def __init__(self, instance) -> None:
        """
        Set self.instance equal to the instance of the model that we're attached
        to. Also, store the content type of that instance.
        """
        self.instance = instance
        self.ct = ContentType.objects.get_for_model(instance)

    def __getattr__(self, name):
        """
        The magic getattr helper. This is called whenever user invokes::

            instance.<attribute>

        Checks if *name* is a valid slug for attributes available to this
        instances. If it is, tries to lookup the :class:`Value` with that
        attribute slug. If there is one, it returns the value of the
        class:`Value` object, otherwise it hasn't been set, so it returns
        None.
        """
        if not name.startswith('_'):
            try:
                attribute = self.get_attribute_by_slug(name)
            except Attribute.DoesNotExist:
                raise AttributeError(
                    _('%(obj)s has no EAV attribute named %(attr)s')
                    % {'obj': self.instance, 'attr': name},
                )

            try:
                return self.get_value_by_attribute(attribute).value
            except Value.DoesNotExist:
                return None

        return getattr(super(), name)

    def get_all_attributes(self):
        """
        Return a query set of all :class:`Attribute` objects that can be set
        for this entity.
        """
        return self.instance._eav_config_cls.get_attributes(
            instance=self.instance,
        ).order_by('display_order')

    def _hasattr(self, attribute_slug):
        """
        Since we override __getattr__ with a backdown to the database, this
        exists as a way of checking whether a user has set a real attribute on
        ourselves, without going to the db if not.
        """
        return attribute_slug in self.__dict__

    def _getattr(self, attribute_slug):
        """
        Since we override __getattr__ with a backdown to the database, this
        exists as a way of getting the value a user set for one of our
        attributes, without going to the db to check.
        """
        return self.__dict__[attribute_slug]

    def save(self):
        """Saves all the EAV values that have been set on this entity."""
        for attribute in self.get_all_attributes():
            if self._hasattr(attribute.slug):
                attribute_value = self._getattr(attribute.slug)
                if (
                    attribute.datatype == Attribute.TYPE_ENUM
                    and not isinstance(
                        attribute_value,
                        EnumValue,
                    )
                    and attribute_value is not None
                ):
                    attribute_value = EnumValue.objects.get(value=attribute_value)
                attribute.save_value(self.instance, attribute_value)

    def validate_attributes(self):
        """
        Called before :meth:`save`, first validate all the entity values to
        make sure they can be created / saved cleanly.
        Raises ``ValidationError`` if they can't be.
        """
        values_dict = self.get_values_dict()

        for attribute in self.get_all_attributes():
            value = None

            # Value was assigned to this instance.
            if self._hasattr(attribute.slug):
                value = self._getattr(attribute.slug)
                values_dict.pop(attribute.slug, None)
            # Otherwise try pre-loaded from DB.
            else:
                value = values_dict.pop(attribute.slug, None)

            if value is None:
                if attribute.required:
                    raise ValidationError(
                        _(f'{attribute.slug} EAV field cannot be blank'),
                    )
            else:
                try:
                    attribute.validate_value(value)
                except ValidationError as e:
                    raise ValidationError(
                        _('%(attr)s EAV field %(err)s')
                        % {'attr': attribute.slug, 'err': e},
                    )

        illegal = values_dict or (
            self.get_object_attributes() - self.get_all_attribute_slugs()
        )

        if illegal:
            raise IllegalAssignmentException(
                'Instance of the class {} cannot have values for attributes: {}.'.format(
                    self.instance.__class__,
                    ', '.join(illegal),
                ),
            )

    def get_values_dict(self):
        return {v.attribute.slug: v.value for v in self.get_values()}

    def get_values(self):
        """Get all set :class:`Value` objects for self.instance."""
        entity_filter = {
            'entity_ct': self.ct,
            f'{get_entity_pk_type(self.instance)}': self.instance.pk,
        }

        return Value.objects.filter(**entity_filter).select_related()

    def get_all_attribute_slugs(self):
        """Returns a list of slugs for all attributes available to this entity."""
        return set(self.get_all_attributes().values_list('slug', flat=True))

    def get_attribute_by_slug(self, slug):
        """Returns a single :class:`Attribute` with *slug*."""
        return self.get_all_attributes().get(slug=slug)

    def get_value_by_attribute(self, attribute):
        """Returns a single :class:`Value` for *attribute*."""
        return self.get_values().get(attribute=attribute)

    def get_object_attributes(self):
        """
        Returns entity instance attributes, except for
        ``instance`` and ``ct`` which are used internally.
        """
        return set(copy(self.__dict__).keys()) - {'instance', 'ct'}

    def __iter__(self):
        """
        Iterate over set eav values. This would allow you to do::

            for i in m.eav: print(i)
        """
        return iter(self.get_values())


class EAVModelMeta(ModelBase):
    def __new__(cls, name, bases, namespace, **kwds):
        result = super().__new__(cls, name, bases, dict(namespace))
        register(result)
        return result
