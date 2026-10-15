from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, cast

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _

from eav import register
from eav.exceptions import IllegalAssignmentException
from eav.logic.entities import config_of, entity_of
from eav.logic.entity_pk import get_entity_pk_type
from eav.logic.schema import OwnSchema, SchemaSource
from eav.models.attribute import Attribute
from eav.models.value import Value

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

#: Names Entity keeps in ``__dict__`` that are not EAV attribute assignments.
_INTERNAL_NAMES = frozenset(("instance", "ct", "_schema"))


class Entity:
    """Helper class that will be attached to entities registered with eav."""

    @staticmethod
    def pre_save_handler(
        sender: type[models.Model],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Validate the entity's attributes before the model instance is saved.

        Attached to the instance as a ``pre_save`` handler; it calls
        :meth:`validate_attributes`.
        """
        entity = entity_of(kwargs["instance"])
        entity.clear_cache()
        entity.validate_attributes()

    @staticmethod
    def post_save_handler(
        sender: type[models.Model],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Save the entity's EAV values after the model instance is saved.

        Attached to the instance as a ``post_save`` handler; it calls :meth:`save`.
        """
        entity_of(kwargs["instance"]).save(created=kwargs.get("created", False))

    def __init__(self, instance: models.Model) -> None:
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

    def _attributes(self) -> Mapping[str, Attribute]:
        """Attributes that apply to this entity, by slug, in display order."""
        return self._schema.load()

    @property
    def _relation(self) -> str:
        """Name of the relation from the instance to its :class:`Value` objects."""
        return config_of(self.instance).generic_relation_attr.lower()

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

    def _values_by_attribute(self) -> dict[Any, Value]:
        """Return the entity's :class:`Value` objects by attribute primary key."""
        if self.instance._state.adding:  # noqa: SLF001
            return {}

        if self._cached_values() is None:
            models.prefetch_related_objects(
                [self.instance],
                models.Prefetch(
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

    def __getattr__(self, name: str) -> Any:
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

        eav_value = self._values_by_attribute().get(attribute.pk)
        return None if eav_value is None else eav_value.value

    def get_all_attributes(self) -> models.QuerySet[Attribute]:
        """Return a query set of the :class:`Attribute` objects this entity can set."""
        attributes = config_of(self.instance).get_attributes(instance=self.instance)
        return attributes.order_by("display_order").select_related("enum_group")

    def _hasattr(self, attribute_slug: str) -> bool:
        """Check whether a user has set a real attribute on this helper.

        Since we override ``__getattr__`` with a fallback to the database, this checks
        without going to the database.
        """
        return attribute_slug in self.__dict__

    def _getattr(self, attribute_slug: str) -> Any:
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
        stored = {} if created else self._values_by_attribute()
        attributes = self._attributes()

        for slug, raw_value in self.assigned_values().items():
            attribute = attributes.get(slug)

            if attribute is not None:
                attribute.store_value(
                    self.instance,
                    attribute.as_choice(raw_value),
                    stored.get(attribute.pk),
                )

        # The stored values changed, so they are loaded again on the next read.
        self._evict_values()

    def validate_attributes(self) -> None:
        """Validate all the entity's values so they can be saved cleanly.

        Called before :meth:`save`. Raises ``ValidationError`` if they can't be.
        """
        stored = self.get_values_dict()
        assigned = self.assigned_values()
        attributes = self._attributes()

        for slug, attribute in attributes.items():
            # A value assigned to this instance wins over the stored one.
            attribute.validate_assignment(
                assigned[slug] if slug in assigned else stored.get(slug),
            )

        known = set(attributes)
        illegal = (set(stored) - known) or (set(assigned) - known)

        if illegal:
            message = (
                "Instance of the class {} cannot have values for attributes: {}."
            ).format(
                self.instance.__class__,
                ", ".join(illegal),
            )
            raise IllegalAssignmentException(message)

    def get_values_dict(self) -> dict[str, Any]:
        """Return the entity's values by attribute slug."""
        return {
            eav_value.attribute.slug: eav_value.value
            for eav_value in self._values_by_attribute().values()
        }

    def get_values(self) -> models.QuerySet[Value]:
        """Get all set :class:`Value` objects for self.instance."""
        entity_filter = {
            "entity_ct": self.ct,
            get_entity_pk_type(type(self.instance)): self.instance.pk,
        }

        return Value.objects.filter(**entity_filter).select_related(
            "attribute",
            "value_enum",
        )

    def get_all_attribute_slugs(self) -> set[str]:
        """Return the slugs of all attributes available to this entity."""
        return set(self._attributes())

    def get_attribute_by_slug(self, slug: str) -> Attribute:
        """Return the :class:`Attribute` with *slug*."""
        if slug not in self._attributes():
            # The attributes may have changed since they were loaded.
            self._schema = OwnSchema(self)

        try:
            return self._attributes()[slug]
        except KeyError as err:
            raise Attribute.DoesNotExist(slug) from err

    def get_value_by_attribute(self, attribute: Attribute) -> Value:
        """Return the :class:`Value` for *attribute*."""
        try:
            return self._values_by_attribute()[attribute.pk]
        except KeyError as err:
            raise Value.DoesNotExist(attribute.slug) from err

    def assigned_values(self) -> dict[str, Any]:
        """
        Return the values assigned to this entity and not yet saved, by attribute slug.

        Names that are not attributes of the entity are included too, so that
        callers can reject them.
        """
        return {name: self.__dict__[name] for name in self.get_object_attributes()}

    def get_object_attributes(self) -> set[str]:
        """Return the names of the attributes assigned to this entity instance.

        Names used internally are excluded.
        """
        return set(self.__dict__) - _INTERNAL_NAMES

    def __iter__(self) -> Iterator[Value]:
        """Iterate over set EAV values.

        This would allow you to do::

            for i in m.eav: print(i)
        """
        return iter(self._values_by_attribute().values())


class EAVModelMeta(ModelBase):
    """Metaclass that registers each model class with eav when it is created."""

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwds: Any,
    ) -> Any:
        """Create the model class and register it with eav."""
        model_class = super().__new__(cls, name, bases, dict(namespace))
        register(cast("type[models.Model]", model_class))
        return model_class
