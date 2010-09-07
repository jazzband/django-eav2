from django.db.models.signals import post_init, post_save
from django.contrib.contenttypes import generic
from .managers import EntityManager
from .models import EavEntity, EavAttribute, EavValue

class EavConfig(object):

    proxy_field_name = 'eav'
    manager_field_name ='objects'
    generic_relation_field_name = 'eav_values'

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
        config_cls = EavRegistry.cache[cls.__name__]['config_cls']

        setattr(instance, config_cls.proxy_field_name, EavEntity(instance))


    @staticmethod
    def register(model_cls, config_cls=EavConfig):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        if model_cls.__name__ in EavRegistry.cache:
            return

        post_init.connect(EavRegistry.attach, sender=model_cls)
        post_save.connect(EavEntity.save_handler, sender=model_cls)
        EavRegistry.cache[model_cls.__name__] = { 'config_cls': 
                                                        config_cls } 

        if hasattr(model_cls, config_cls.manager_field_name):
            mgr = getattr(model_cls, config_cls.manager_field_name)
            EavRegistry.cache[model_cls.__name__]['old_mgr'] = mgr

        setattr(model_cls, config_cls.proxy_field_name, EavEntity)

        setattr(getattr(model_cls, config_cls.proxy_field_name),
                        'get_eav_attributes', config_cls.get_eav_attributes)

        mgr = EntityManager()
        mgr.contribute_to_class(model_cls, config_cls.manager_field_name)

        gr_name = config_cls.generic_relation_field_name
        generic_relation = generic.GenericRelation(EavValue,
                                                object_id_field='entity_id',
                                                content_type_field='entity_ct')
        generic_relation.contribute_to_class(model_cls, gr_name)



    @staticmethod
    def unregister(model_cls):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        if not model_cls.__name__ in EavRegistry.cache:
            return

        cache = EavRegistry.cache[model_cls.__name__]
        config_cls = cache['config_cls']
        
        post_init.disconnect(EavRegistry.attach, sender=model_cls)
        post_save.disconnect(EavEntity.save_handler, sender=model_cls)
        
        try:
            delattr(model_cls, config_cls.manager_field_name)
        except AttributeError:
            pass

        try:
            delattr(model_cls, config_cls.generic_relation_field_name)
        except AttributeError:
            pass

        if 'old_mgr' in cache:
            cache['old_mgr'].contribute_to_class(model_cls, 
                                                config_cls.manager_field_name)

        try:
            delattr(model_cls, config_cls.proxy_field_name)
        except AttributeError:
            pass

        EavRegistry.cache.pop(model_cls.__name__)

