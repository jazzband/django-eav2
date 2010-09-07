from django.db.models.signals import post_init, pre_save
from .managers import EntityManager
from .models import EavEntity, EavAttribute

class EavConfig(object):

    proxy_field_name = 'eav'
    manager_field_name ='objects'

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
    cache = {}

    @staticmethod
    def attach(sender, *args, **kwargs):
        """
            Attache EAV toolkit to an instance after init.
        """
        instance = kwargs['instance']
        cls = instance.__class__
        admin_cls = EavRegistry.cache[cls.__name__]['admin_cls']

        setattr(instance, admin_cls.proxy_field_name, EavEntity(instance))


    @staticmethod
    def register(model_cls, admin_cls=EavConfig):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        if model_cls.__name__ in EavRegistry.cache:
            return

        post_init.connect(EavRegistry.attach, sender=model_cls)
        pre_save.connect(EavEntity.pre_save_handler, sender=model_cls)
        EavRegistry.cache[model_cls.__name__] = { 'admin_cls': 
                                                        admin_cls } 

        if hasattr(model_cls, admin_cls.manager_field_name):
            mgr = getattr(model_cls, admin_cls.manager_field_name)
            EavRegistry.cache[model_cls.__name__]['old_mgr'] = mgr

        setattr(model_cls, admin_cls.proxy_field_name, EavEntity)

        setattr(getattr(model_cls, admin_cls.proxy_field_name),
                        'get_eav_attributes', admin_cls.get_eav_attributes)

        mgr = EntityManager()
        mgr.contribute_to_class(model_cls, admin_cls.manager_field_name)


    @staticmethod
    def unregister(model_cls):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        if not model_cls.__name__ in EavRegistry.cache:
            return

        cache = EavRegistry.cache[model_cls.__name__]
        admin_cls = cache['admin_cls']
        
        post_init.disconnect(EavRegistry.attach, sender=model_cls)
        pre_save.disconnect(EavEntity.pre_save_handler, sender=model_cls)
        
        try:
            delattr(model_cls, admin_cls.manager_field_name)
        except AttributeError:
            pass

        if 'old_mgr' in cache:
            cache['old_mgr'].contribute_to_class(model_cls, 
                                                admin_cls.manager_field_name)

        try:
            delattr(model_cls, admin_cls.proxy_field_name)
        except AttributeError:
            pass

        EavRegistry.cache.pop(model_cls.__name__)

