from django.contrib.contenttypes import generic
from django.db.utils import DatabaseError
from django.db.models.signals import post_init, post_save, post_delete
from .managers import EntityManager
from .models import (EavEntity, EavAttribute, EavValue, 
                     get_unique_class_identifier)

class EavConfig(EavEntity):

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
    def get_config_cls_for_model(model_cls):
        """
            Returns the configuration class for the given
            model
        """
        cls_id = get_unique_class_identifier(model_cls)

        if cls_id in EavRegistry.cache:
            return EavRegistry.cache[cls_id]['config_cls']


    @staticmethod
    def attach(sender, *args, **kwargs):
        """
            Attache EAV toolkit to an instance after init.
        """
        instance = kwargs['instance']
        config_cls = EavRegistry.get_config_cls_for_model(sender)

        setattr(instance, config_cls.proxy_field_name, EavEntity(instance))


    @staticmethod
    def update_attribute_cache(sender, *args, **kwargs):
        """
            Update the attribute cache for all the models every time we
            create an attribute.
        """
        for cache in EavRegistry.cache.itervalues():
            EavEntity.update_attr_cache_for_model(cache['model_cls'])

    
    @staticmethod
    def wrap_config_class(model_cls, config_cls):
        """
            Check if the config class is EavConfig, and create a subclass if
            it is
        """
        if config_cls is EavConfig:
            return type("%sConfig" % model_cls.__name__, (EavConfig,), {})
        return config_cls


    @staticmethod
    def register(model_cls, config_cls=EavConfig):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        
        cls_id = get_unique_class_identifier(model_cls)
        
        if cls_id in EavRegistry.cache:
            return
        
        config_cls = EavRegistry.wrap_config_class(model_cls, config_cls)
        post_init.connect(EavRegistry.attach, sender=model_cls)
        post_save.connect(EavEntity.save_handler, sender=model_cls)
        EavRegistry.cache[cls_id] = { 'config_cls': config_cls,
                                      'model_cls': model_cls } 

        if hasattr(model_cls, config_cls.manager_field_name):
            mgr = getattr(model_cls, config_cls.manager_field_name)
            EavRegistry.cache[cls_id]['old_mgr'] = mgr

        setattr(model_cls, config_cls.proxy_field_name, config_cls)
        
        setattr(getattr(model_cls, config_cls.proxy_field_name),
                        'get_eav_attributes', config_cls.get_eav_attributes)

        mgr = EntityManager()
        mgr.contribute_to_class(model_cls, config_cls.manager_field_name)
        
        
        try:
            EavEntity.update_attr_cache_for_model(model_cls)
        except DatabaseError:
            pass

        gr_name = config_cls.generic_relation_field_name
        generic_relation = generic.GenericRelation(EavValue,
                                                   object_id_field='entity_id',
                                                   content_type_field='entity_ct',
                                                   related_name=model_cls.__name__)
        generic_relation.contribute_to_class(model_cls, gr_name)


    @staticmethod
    def unregister(model_cls):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        cls_id = get_unique_class_identifier(model_cls)
        
        if not cls_id in EavRegistry.cache:
            return

        cache = EavRegistry.cache[cls_id]
        config_cls = cache['config_cls']
        post_init.disconnect(EavRegistry.attach, sender=model_cls)
        post_save.disconnect(EavEntity.save_handler, sender=model_cls)
        
        try:
            delattr(model_cls, config_cls.manager_field_name)
        except AttributeError:
            pass

        try:
            delattr(model_cls, config_cls.generic_relation_field_name)
            #delattr(EavValue, config_cls.generic_relation_field_name)
        except AttributeError:
            pass

        if 'old_mgr' in cache:
            cache['old_mgr'].contribute_to_class(model_cls, 
                                                config_cls.manager_field_name)

        try:
            delattr(model_cls, config_cls.proxy_field_name)
        except AttributeError:
            pass

        EavEntity.flush_attr_cache_for_model(model_cls)
        EavRegistry.cache.pop(cls_id)
        
        
     # todo : test cache
     # todo : tst unique identitfier  
     # todo:  test update attribute cache on attribute creation
     
post_save.connect(EavRegistry.update_attribute_cache, sender=EavAttribute)
post_delete.connect(EavRegistry.update_attribute_cache, sender=EavAttribute)
