from django.db.models.signals import post_init
from .managers import EntityManager
from .models import EavEntity, EavAttribute

class EavConfig(object):
    @classmethod
    def get_eav_attributes(cls):
        """
             By default, all attributes apply to an entity,
             unless otherwise specified.
        """
        return EavAttribute.objects.all()
        

class EavRegistry(object):
    """
        Tools to add eav features to models
    """
    field_cache = {}

    @staticmethod
    def attach(sender, *args, **kwargs):
        """
            Attache EAV toolkit to an instance after init.
        """
        instance = kwargs['instance']
        cls = instance.__class__

        proxy_name = EavRegistry.field_cache[cls.__name__]['proxy']

        setattr(instance, proxy_name, EavEntity(instance))


    @staticmethod
    def register(model_cls, admin_cls=EavConfig, eav_proxy_field='eav',
                 eav_manager_field='objects'):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        if model_cls.__name__ in EavRegistry.field_cache:
            return

        post_init.connect(EavRegistry.attach, sender=model_cls)
        EavRegistry.field_cache[model_cls.__name__] = {
                                                   'proxy': eav_proxy_field,
                                                   'mgr': eav_manager_field}

        if hasattr(model_cls, eav_manager_field):
            mgr = getattr(model_cls, eav_manager_field)
            EavRegistry.field_cache[model_cls.__name__]['old_mgr'] = mgr

        setattr(model_cls, eav_proxy_field, EavEntity)

        setattr(getattr(model_cls, eav_proxy_field),
                        'get_eav_attributes', admin_cls.get_eav_attributes)

        mgr = EntityManager()
        mgr.contribute_to_class(model_cls, eav_manager_field)


    @staticmethod
    def unregister(model_cls):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        if not model_cls.__name__ in EavRegistry.field_cache:
            return

        cache = EavRegistry.field_cache[model_cls.__name__]
        post_init.disconnect(EavRegistry.attach, sender=model_cls)
        proxy_name = cache['proxy']
        mgr_name = cache['mgr']

        try:
            delattr(model_cls, mgr_name)
        except AttributeError:
            pass

        if 'old_mgr' in cache:
            cache['old_mgr'].contribute_to_class(model_cls, mgr_name)

        try:
            delattr(model_cls, proxy_name)
        except AttributeError:
            pass

        EavRegistry.field_cache.pop(model_cls.__name__)

