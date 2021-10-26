"""This modules contains the registry classes."""

from django.contrib.contenttypes import fields as generic
from django.db.models.signals import post_init, post_save, pre_save

from eav.managers import EntityManager
from eav.models import Attribute, Entity, Value

from eav.logic.entity_pk import get_entity_pk_type


class EavConfig(object):
    """
    The default ``EavConfig`` class used if it is not overriden on registration.
    This is where all the default eav attribute names are defined.

    Available options are as follows:

    1. manager_attr - Specifies manager name. Used to refer to the
       manager from Entity class, "objects" by default.
    2. manager_only - Specifies whether signals and generic relation should
       be setup for the registered model.
    3. eav_attr - Named of the Entity toolkit instance on the registered
       model instance. "eav" by default. See attach_eav_attr.
    4. generic_relation_attr - Name of the GenericRelation to Value
       objects. "eav_values" by default.
    5. generic_relation_related_name - Name of the related name for
       GenericRelation from Entity to Value. None by default. Therefore,
       if not overridden, it is not possible to query Values by Entities.
    """

    manager_attr = 'objects'
    manager_only = False
    eav_attr = 'eav'
    generic_relation_attr = 'eav_values'
    generic_relation_related_name = None

    @classmethod
    def get_attributes(cls, instance=None):
        """
        By default, all :class:`~eav.models.Attribute` object apply to an
        entity, unless you provide a custom EavConfig class overriding this.
        """
        return Attribute.objects.all()


class Registry(object):
    """
    Handles registration through the
    :meth:`register` and :meth:`unregister` methods.
    """

    @staticmethod
    def register(model_cls, config_cls=None):
        """
        Registers *model_cls* with eav. You can pass an optional *config_cls*
        to override the EavConfig defaults.

        .. note::
           Multiple registrations for the same entity are harmlessly ignored.
        """
        if hasattr(model_cls, '_eav_config_cls'):
            return

        if config_cls is EavConfig or config_cls is None:
            config_cls = type("%sConfig" % model_cls.__name__, (EavConfig,), {})

        # set _eav_config_cls on the model so we can access it there
        setattr(model_cls, '_eav_config_cls', config_cls)

        reg = Registry(model_cls)
        reg._register_self()

    @staticmethod
    def unregister(model_cls):
        """
        Unregisters *model_cls* with eav.

        .. note::
           Unregistering a class not already registered is harmlessly ignored.
        """
        if not getattr(model_cls, '_eav_config_cls', None):
            return
        reg = Registry(model_cls)
        reg._unregister_self()

        delattr(model_cls, '_eav_config_cls')

    @staticmethod
    def attach_eav_attr(sender, *args, **kwargs):
        """
        Attach EAV Entity toolkit to an instance after init.
        """
        instance = kwargs['instance']
        config_cls = instance.__class__._eav_config_cls
        setattr(instance, config_cls.eav_attr, Entity(instance))

    def __init__(self, model_cls):
        """
        Set the *model_cls* and its *config_cls*
        """
        self.model_cls = model_cls
        self.config_cls = model_cls._eav_config_cls

    def _attach_manager(self):
        """
        Attach the manager to *manager_attr* specified in *config_cls*
        """
        # Save the old manager if the attribute name conflicts with the new one.
        if hasattr(self.model_cls, self.config_cls.manager_attr):
            mgr = getattr(self.model_cls, self.config_cls.manager_attr)

            # For some models, `local_managers` may be empty, eg.
            # django.contrib.auth.models.User and AbstractUser
            if mgr in self.model_cls._meta.local_managers:
                self.config_cls.old_mgr = mgr
                self.model_cls._meta.local_managers.remove(mgr)

            self.model_cls._meta._expire_cache()

        # Attach the new manager to the model.
        mgr = EntityManager()
        mgr.contribute_to_class(self.model_cls, self.config_cls.manager_attr)

    def _detach_manager(self):
        """
        Detach the manager and restore the previous one (if there was one).
        """
        mgr = getattr(self.model_cls, self.config_cls.manager_attr)
        self.model_cls._meta.local_managers.remove(mgr)
        self.model_cls._meta._expire_cache()
        delattr(self.model_cls, self.config_cls.manager_attr)

        if hasattr(self.config_cls, 'old_mgr'):
            self.config_cls.old_mgr.contribute_to_class(
                self.model_cls, self.config_cls.manager_attr
            )

    def _attach_signals(self):
        """
        Attach pre- and post- save signals from model class
        to Entity helper. This way, Entity instance will be
        able to prepare and clean-up before and after creation /
        update of the user's model class instance.
        """
        post_init.connect(Registry.attach_eav_attr, sender=self.model_cls)
        pre_save.connect(Entity.pre_save_handler, sender=self.model_cls)
        post_save.connect(Entity.post_save_handler, sender=self.model_cls)

    def _detach_signals(self):
        """
        Detach all signals for eav.
        """
        post_init.disconnect(Registry.attach_eav_attr, sender=self.model_cls)
        pre_save.disconnect(Entity.pre_save_handler, sender=self.model_cls)
        post_save.disconnect(Entity.post_save_handler, sender=self.model_cls)

    def _attach_generic_relation(self):
        """Set up the generic relation for the entity."""
        rel_name = (
            self.config_cls.generic_relation_related_name or self.model_cls.__name__
        )

        gr_name = self.config_cls.generic_relation_attr.lower()
        generic_relation = generic.GenericRelation(
            Value,
            object_id_field=get_entity_pk_type(self.model_cls),
            content_type_field='entity_ct',
            related_query_name=rel_name,
        )
        generic_relation.contribute_to_class(self.model_cls, gr_name)

    def _detach_generic_relation(self):
        """
        Remove the generic relation from the entity
        """
        gen_rel_field = self.config_cls.generic_relation_attr.lower()
        for field in self.model_cls._meta.local_many_to_many:
            if field.name == gen_rel_field:
                self.model_cls._meta.local_many_to_many.remove(field)
                break

        delattr(self.model_cls, gen_rel_field)

    def _register_self(self):
        """
        Call the necessary registration methods
        """
        self._attach_manager()

        if not self.config_cls.manager_only:
            self._attach_signals()
            self._attach_generic_relation()

    def _unregister_self(self):
        """
        Call the necessary unregistration methods
        """
        self._detach_manager()

        if not self.config_cls.manager_only:
            self._detach_signals()
            self._detach_generic_relation()
