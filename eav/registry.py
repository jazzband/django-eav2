"""This modules contains the registry classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from django.contrib.contenttypes import fields as generic
from django.db.models.signals import post_init, post_save, pre_save

from eav.logic.entity_pk import get_entity_pk_type
from eav.managers import EntityManager
from eav.models import Attribute, Entity, Value

if TYPE_CHECKING:
    from django.db.models import Manager, Model, QuerySet

_CONFIG_ATTR: Final = "_eav_config_cls"


class EavConfig:
    """The default ``EavConfig`` class, used if it is not overridden on registration.

    This is where all the default eav attribute names are defined.

    Available options are as follows:

    1. manager_attr - Specifies manager name. Used to refer to the
       manager from Entity class, "objects" by default.
    2. manager_only - Specifies whether signals and generic relation should
       be setup for the registered model.
    3. eav_attr - Name of the Entity helper on the registered model instance,
       and the prefix of its lookups. "eav" by default. See attach_eav_attr.
    4. generic_relation_attr - Name of the GenericRelation to Value
       objects. "eav_values" by default.
    5. bulk_batch_size - How many entities ``bulk_create`` and ``bulk_update``
       write at a time, and the most rows in one ``INSERT`` statement. 1000 by
       default; the ``batch_size`` argument of those methods overrides it.
    6. cache_values - Whether ``instance.eav.<slug>`` loads the values once
       and reuses them, which is the default. Set to ``False`` for models whose
       values are written outside ``instance.eav`` and ``save()``; every read
       then queries the database.
    7. generic_relation_related_name - Name used to query Value objects from an
       entity, for example ``Value.objects.filter(Patient__name="Ada")``. None by
       default, which uses the model class name.
    """

    manager_attr: str = "objects"
    bulk_batch_size: int = 1000
    cache_values: bool = True
    manager_only: bool = False
    eav_attr: str = "eav"
    generic_relation_attr: str = "eav_values"
    generic_relation_related_name: str | None = None
    old_mgr: Manager[Any] | None = None

    @classmethod
    def shares_attributes(cls) -> bool:
        """
        Whether every entity of the model has the same attributes.

        This is the case unless :meth:`get_attributes` is overridden, since an
        override may choose attributes per instance.
        """
        return all(
            "get_attributes" not in klass.__dict__
            for klass in cls.__mro__
            if klass is not EavConfig
        )

    @classmethod
    def get_attributes(cls, instance: Model | None = None) -> QuerySet[Attribute]:
        """Return the attributes of an entity, which are all of them by default.

        By default, all :class:`~eav.models.Attribute` objects apply to an entity,
        unless you provide a custom EavConfig class overriding this.
        """
        return Attribute.objects.all()


class Registry:
    """The registration of models with eav: :meth:`register` and :meth:`unregister`."""

    def __init__(self, model_cls: type[Model]) -> None:
        """Set the *model_cls* and its *config_cls*."""
        # Models get their ``_eav_config_cls`` when they are registered.
        self.model_cls: Any = model_cls
        self.config_cls: type[EavConfig] = getattr(model_cls, _CONFIG_ATTR)

    @staticmethod
    def register(
        model_cls: type[Model],
        config_cls: type[EavConfig] | None = None,
    ) -> None:
        """Register *model_cls* with eav, optionally with a custom *config_cls*.

        You can pass an optional *config_cls* to override the EavConfig defaults.

        .. note::
           Multiple registrations for the same entity are harmlessly ignored.
        """
        if hasattr(model_cls, _CONFIG_ATTR):
            return

        if config_cls is EavConfig or config_cls is None:
            config_cls = type(f"{model_cls.__name__}Config", (EavConfig,), {})

        # set _eav_config_cls on the model so we can access it there
        setattr(model_cls, _CONFIG_ATTR, config_cls)

        reg = Registry(model_cls)
        reg._register_self()

    @staticmethod
    def unregister(model_cls: type[Model]) -> None:
        """
        Unregisters *model_cls* with eav.

        .. note::
           Unregistering a class not already registered is harmlessly ignored.
        """
        if not getattr(model_cls, _CONFIG_ATTR, None):
            return
        reg = Registry(model_cls)
        reg._unregister_self()

        delattr(model_cls, _CONFIG_ATTR)

    @staticmethod
    def attach_eav_attr(sender: type[Model], *args: Any, **kwargs: Any) -> None:
        """Attach the EAV Entity helper to an instance after init."""
        instance: Any = kwargs["instance"]
        setattr(instance, instance._eav_config_cls.eav_attr, Entity(instance))

    def _attach_manager(self) -> None:
        """
        Attach the EntityManager to the model class.

        This method replaces the existing manager specified in the `config_cls`
        with a new instance of `EntityManager`. If the specified manager is the
        default manager, the `EntityManager` is set as the new default manager.
        Otherwise, it is appended to the list of managers.

        If the model class already has a manager with the same name as the one
        specified in `config_cls`, it is saved as `old_mgr` in the `config_cls`
        for use during detachment.
        """
        manager_attr = self.config_cls.manager_attr
        model_meta = self.model_cls._meta
        current_manager = getattr(self.model_cls, manager_attr, None)

        if isinstance(current_manager, EntityManager):
            # EntityManager is already attached, no need to proceed
            return

        # Create a new EntityManager
        new_manager: EntityManager[Any] = EntityManager()

        # Save and remove the old manager if it exists
        if current_manager and current_manager in model_meta.local_managers:
            self.config_cls.old_mgr = current_manager
            model_meta.local_managers.remove(current_manager)

            # Set the creation_counter to maintain the order
            # This ensures that the new manager has the same priority as the old one
            new_manager.creation_counter = current_manager.creation_counter

        # Attach the new EntityManager instance to the model.
        new_manager.contribute_to_class(self.model_cls, manager_attr)

    def _detach_manager(self) -> None:
        """Detach the manager and restore the previous one (if there was one)."""
        mgr = getattr(self.model_cls, self.config_cls.manager_attr)
        self.model_cls._meta.local_managers.remove(mgr)
        self.model_cls._meta._expire_cache()
        delattr(self.model_cls, self.config_cls.manager_attr)

        if self.config_cls.old_mgr is not None:
            self.config_cls.old_mgr.contribute_to_class(
                self.model_cls,
                self.config_cls.manager_attr,
            )

    def _attach_signals(self) -> None:
        """Attach pre- and post-save signals from the model class to the Entity helper.

        This way, the Entity instance will be able to prepare and clean up before and
        after creation / update of the user's model class instance.
        """
        post_init.connect(Registry.attach_eav_attr, sender=self.model_cls)
        pre_save.connect(Entity.pre_save_handler, sender=self.model_cls)
        post_save.connect(Entity.post_save_handler, sender=self.model_cls)

    def _detach_signals(self) -> None:
        """Detach all signals for eav."""
        post_init.disconnect(Registry.attach_eav_attr, sender=self.model_cls)
        pre_save.disconnect(Entity.pre_save_handler, sender=self.model_cls)
        post_save.disconnect(Entity.post_save_handler, sender=self.model_cls)

    def _attach_generic_relation(self) -> None:
        """Set up the generic relation for the entity."""
        rel_name = (
            self.config_cls.generic_relation_related_name or self.model_cls.__name__
        )

        gr_name = self.config_cls.generic_relation_attr.lower()
        generic_relation = generic.GenericRelation(
            Value,
            object_id_field=get_entity_pk_type(self.model_cls),
            content_type_field="entity_ct",
            related_query_name=rel_name,
        )
        generic_relation.contribute_to_class(self.model_cls, gr_name)

    def _detach_generic_relation(self) -> None:
        """Remove the generic relation from the entity."""
        gen_rel_field = self.config_cls.generic_relation_attr.lower()
        for field in self.model_cls._meta.local_many_to_many:
            if field.name == gen_rel_field:
                self.model_cls._meta.local_many_to_many.remove(field)
                break

        delattr(self.model_cls, gen_rel_field)

    def _register_self(self) -> None:
        """Call the necessary registration methods."""
        self._attach_manager()

        if not self.config_cls.manager_only:
            self._attach_signals()
            self._attach_generic_relation()

    def _unregister_self(self) -> None:
        """Call the necessary unregistration methods."""
        self._detach_manager()

        if not self.config_cls.manager_only:
            self._detach_signals()
            self._detach_generic_relation()
