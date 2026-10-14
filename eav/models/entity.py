from __future__ import annotations

from copy import copy
from functools import cached_property
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch, QuerySet, prefetch_related_objects
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _

from eav import register
from eav.exceptions import IllegalAssignmentException
from eav.logic.entity_pk import get_entity_pk_type
from eav.logic.schema import OwnSchema, SchemaSource
from eav.models.attribute import Attribute
from eav.models.enum_value import EnumValue
from eav.models.value import Value

#: Names Entity keeps in ``__dict__`` that are not EAV attribute assignments.
_INTERNAL_NAMES = frozenset(("instance", "ct", "_schema"))


class Entity:
    """Helper class that will be attached to entities registered with eav."""

    @staticmethod
    def pre_save_handler(sender, *args, **kwargs):
        """Validate the entity's attributes before the model instance is saved.

        Attached to the instance as a ``pre_save`` handler; it calls
        :meth:`validate_attributes`.
        """
        instance = kwargs["instance"]
        entity = getattr(kwargs["instance"], instance._eav_config_cls.eav_attr)  # noqa: SLF001
        entity.clear_cache()
        entity.validate_attributes()

    @staticmethod
    def post_save_handler(sender, *args, **kwargs):
        """Save the entity's EAV values after the model instance is saved.

        Attached to the instance as a ``post_save`` handler; it calls :meth:`save`.
        """
        instance = kwargs["instance"]
        entity = getattr(instance, instance._eav_config_cls.eav_attr)  # noqa: SLF001
        entity.save(created=kwargs.get("created", False))

    def __init__(self, instance) -> None:
        """Attach the helper to *instance*, the model instance it belongs to."""
        self.instance = instance
        self._schema: SchemaSource = OwnSchema(self)

    @cached_property
    def ct(self) -> ContentType:
        """The content type of the instance, looked up on first use."""
        return ContentType.objects.get_for_model(self.instance)

    def clear_cache(self) -> None:
        """
        Forget the values and attributes loaded for this entity.

        Reading ``instance.eav.<slug>`` loads all of the entity's values once,
        into the instance's ``prefetch_related`` cache, and reuses them. That
        cache is cleared when the instance is saved or refreshed with
        ``refresh_from_db()``; call this after changing values elsewhere
        (another process, a raw query) if you need to read them again.
        """
        self._evict_values()
        self._schema = OwnSchema(self)

    def use_schema(self, source: SchemaSource) -> None:
        """Read the attributes from *source*, for example one shared by a queryset."""
        self._schema = source

    def _attributes(self):
        """Attributes that apply to this entity, by slug, in display order."""
        return self._schema.load()

    @property
    def _relation(self) -> str:
        """Name of the relation from the instance to its :class:`Value` objects."""
        config_cls = self.instance._eav_config_cls  # noqa: SLF001
        return str(config_cls.generic_relation_attr).lower()

    def _cached_values(self) -> list[Value] | None:
        """
        Values already on the instance, from ``prefetch_related`` or from us.

        ``None`` means they have not been loaded.
        """
        prefetched = getattr(self.instance, "_prefetched_objects_cache", {})
        queryset = prefetched.get(self._relation)
        return None if queryset is None else list(queryset)

    def _evict_values(self) -> None:
        """Drop the values from the instance, as ``refresh_from_db()`` does."""
        getattr(self.instance, "_prefetched_objects_cache", {}).pop(
            self._relation,
            None,
        )

    def _values(self) -> dict[Any, Value]:
        """Return the entity's :class:`Value` objects by attribute primary key."""
        if self.instance._state.adding:  # noqa: SLF001
            return {}

        if self._cached_values() is None:
            prefetch_related_objects(
                [self.instance],
                Prefetch(
                    self._relation,
                    queryset=Value.objects.select_related("attribute", "value_enum"),
                ),
            )

        cached = self._cached_values() or ()
        return {eav_value.attribute.pk: eav_value for eav_value in cached}

    def _loaded_value(self, slug: str) -> Value | None:
        """
        Find an already loaded value by attribute slug.

        This avoids loading the attributes for every instance of a list that
        was fetched with ``prefetch_related``.
        """
        for eav_value in self._cached_values() or ():
            if eav_value.attribute.slug == slug:
                return eav_value

        return None

    def __getattr__(self, name):
        """Return the value of the EAV attribute called *name*.

        This is called whenever the user invokes::

            instance.<attribute>

        Checks if *name* is a valid slug for attributes available to this
        instances. If it is, tries to lookup the :class:`Value` with that
        attribute slug. If there is one, it returns the value of the
        class:`Value` object, otherwise it hasn't been set, so it returns
        None.
        """
        if name.startswith("_"):
            return getattr(super(), name)

        loaded = self._loaded_value(name)

        if loaded is not None:
            return loaded.value

        try:
            attribute = self.get_attribute_by_slug(name)
        except Attribute.DoesNotExist as err:
            raise AttributeError(
                _("%(obj)s has no EAV attribute named %(attr)s")
                % {"obj": self.instance, "attr": name},
            ) from err

        eav_value = self._values().get(attribute.pk)
        return None if eav_value is None else eav_value.value

    def get_all_attributes(self) -> QuerySet[Attribute]:
        """Return a query set of the :class:`Attribute` objects this entity can set."""
        config_cls = self.instance._eav_config_cls  # noqa: SLF001
        attributes: QuerySet[Attribute] = config_cls.get_attributes(
            instance=self.instance,
        )
        return attributes.order_by("display_order").select_related("enum_group")

    def _hasattr(self, attribute_slug):
        """Check whether a user has set a real attribute on this helper.

        Since we override ``__getattr__`` with a fallback to the database, this checks
        without going to the database.
        """
        return attribute_slug in self.__dict__

    def _getattr(self, attribute_slug):
        """Get the value a user set for one of our attributes.

        Since we override ``__getattr__`` with a fallback to the database, this reads
        it without going to the database.
        """
        return self.__dict__[attribute_slug]

    def save(self, *, created: bool = False) -> None:
        """
        Save all the EAV values that have been set on this entity.

        Pass ``created=True`` for an entity that was just inserted, which has no
        values to look up.
        """
        values = {} if created else self._values()

        for attribute in self._attributes().values():
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
                    attribute_value = attribute.enum_choices.get(
                        attribute_value,
                    ) or EnumValue.objects.get(value=attribute_value)

                attribute.store_value(
                    self.instance,
                    attribute_value,
                    values.get(attribute.pk),
                )

        # The stored values changed, so they are loaded again on the next read.
        self._evict_values()

    def validate_attributes(self):
        """Validate all the entity's values so they can be saved cleanly.

        Called before :meth:`save`. Raises ``ValidationError`` if they can't be.
        """
        values_dict = self.get_values_dict()

        for attribute in self._attributes().values():
            value = None

            # Value was assigned to this instance.
            if self._hasattr(attribute.slug):
                value = self._getattr(attribute.slug)
                values_dict.pop(attribute.slug, None)
            # Otherwise try pre-loaded from DB.
            else:
                value = values_dict.pop(attribute.slug, None)

            attribute.validate_assignment(value)

        illegal = values_dict or (
            self.get_object_attributes() - self.get_all_attribute_slugs()
        )

        if illegal:
            message = (
                "Instance of the class {} cannot have values for attributes: {}."
            ).format(
                self.instance.__class__,
                ", ".join(illegal),
            )
            raise IllegalAssignmentException(message)

    def get_values_dict(self):
        """Return the entity's values by attribute slug."""
        return {
            eav_value.attribute.slug: eav_value.value
            for eav_value in self._values().values()
        }

    def get_values(self):
        """Get all set :class:`Value` objects for self.instance."""
        entity_filter = {
            "entity_ct": self.ct,
            f"{get_entity_pk_type(self.instance)}": self.instance.pk,
        }

        return Value.objects.filter(**entity_filter).select_related(
            "attribute",
            "value_enum",
        )

    def get_all_attribute_slugs(self):
        """Return the slugs of all attributes available to this entity."""
        return set(self._attributes())

    def get_attribute_by_slug(self, slug):
        """Return the :class:`Attribute` with *slug*."""
        if slug not in self._attributes():
            # The attributes may have changed since they were loaded.
            self._schema = OwnSchema(self)

        try:
            return self._attributes()[slug]
        except KeyError as err:
            raise Attribute.DoesNotExist(slug) from err

    def get_value_by_attribute(self, attribute):
        """Return the :class:`Value` for *attribute*."""
        try:
            return self._values()[attribute.pk]
        except KeyError as err:
            raise Value.DoesNotExist(attribute.slug) from err

    def assigned_values(self) -> dict[str, Any]:
        """
        Return the values assigned to this entity and not yet saved, by attribute slug.

        Names that are not attributes of the entity are included too, so that
        callers can reject them.
        """
        return {name: self.__dict__[name] for name in self.get_object_attributes()}

    def get_object_attributes(self):
        """Return the names of the attributes assigned to this entity instance.

        Names used internally are excluded.
        """
        return set(copy(self.__dict__).keys()) - _INTERNAL_NAMES

    def __iter__(self):
        """Iterate over set EAV values.

        This would allow you to do::

            for i in m.eav: print(i)
        """
        return iter(self._values().values())


class EAVModelMeta(ModelBase):
    """Metaclass that registers each model class with eav when it is created."""

    def __new__(cls, name, bases, namespace, **kwds):
        """Create the model class and register it with eav."""
        result = super().__new__(cls, name, bases, dict(namespace))
        register(result)
        return result
