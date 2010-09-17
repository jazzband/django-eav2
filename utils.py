#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
#
#    This software is derived from EAV-Django originally written and 
#    copyrighted by Andrey Mikhaylenko <http://pypi.python.org/pypi/eav-django>
#
#    This is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This software is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with EAV-Django.  If not, see <http://gnu.org/licenses/>.

from django.contrib.contenttypes import generic
from django.db.utils import DatabaseError
from django.db.models.signals import post_init, post_save, post_delete, pre_init
from .managers import EntityManager
from .models import (EavEntity, EavAttribute, EavValue, 
                     get_unique_class_identifier)


#todo : rename this file in registry
class EavConfig(EavEntity):

    proxy_field_name = 'eav'
    manager_field_name ='objects'
    generic_relation_field_name = 'eav_values'
    generic_relation_field_related_name = None

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
            it is. We don't want to use eav_config directly since we use the 
            class as a name space
        """
        if config_cls is EavConfig:
            return type("%sConfig" % model_cls.__name__, (EavConfig,), {})
        return config_cls


    @staticmethod
    def register(model_cls, config_cls=EavConfig, manager_only=False):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        
        cls_id = get_unique_class_identifier(model_cls)
        
        if cls_id in EavRegistry.cache:
            return
        
        config_cls = EavRegistry.wrap_config_class(model_cls, config_cls)
        
        if not manager_only:
            # we want to call attach and save handler on instance creation and
            # saving            
            post_init.connect(EavRegistry.attach, sender=model_cls)
            post_save.connect(EavEntity.save_handler, sender=model_cls)
        
        # todo: rename cache in data
        EavRegistry.cache[cls_id] = { 'config_cls': config_cls,
                                      'model_cls': model_cls,
                                      'manager_only': manager_only } 

        # save the old manager if the attribute name conflict with the new
        # one
        if hasattr(model_cls, config_cls.manager_field_name):
            mgr = getattr(model_cls, config_cls.manager_field_name)
            EavRegistry.cache[cls_id]['old_mgr'] = mgr

        if not manager_only:
            # set add the config_cls as an attribute of the model
            # it will allow to perform some operation directly from this model
            setattr(model_cls, config_cls.proxy_field_name, config_cls)
            
            # todo : not useful anymore ?
            setattr(getattr(model_cls, config_cls.proxy_field_name),
                            'get_eav_attributes', config_cls.get_eav_attributes)

        # attache the new manager to the model
        mgr = EntityManager()
        mgr.contribute_to_class(model_cls, config_cls.manager_field_name)
        
        if not manager_only:
            # todo: see with david how to change that
            try:
                EavEntity.update_attr_cache_for_model(model_cls)
            except DatabaseError:
                pass

            # todo: make that overridable
            # attach the generic relation to the model
            if config_cls.generic_relation_field_related_name:
                rel_name = config_cls.generic_relation_field_related_name
            else:
                rel_name = model_cls.__name__
            gr_name = config_cls.generic_relation_field_name.lower()
            generic_relation = generic.GenericRelation(EavValue,
                                                       object_id_field='entity_id',
                                                       content_type_field='entity_ct',
                                                       related_name=rel_name)
            generic_relation.contribute_to_class(model_cls, gr_name)

    @staticmethod
    def unregister(model_cls):
        """
            Do the INVERSE of 'Inject eav features into the given model 
            and attach a signal listener to it for setup.'
        """
        cls_id = get_unique_class_identifier(model_cls)
        
        if not cls_id in EavRegistry.cache:
            return

        cache = EavRegistry.cache[cls_id]
        config_cls = cache['config_cls']
        manager_only = cache['manager_only']
        if not manager_only:
            post_init.disconnect(EavRegistry.attach, sender=model_cls)
            post_save.disconnect(EavEntity.save_handler, sender=model_cls)
        
        try:
            delattr(model_cls, config_cls.manager_field_name)
        except AttributeError:
            pass

        # remove remaining reference to the generic relation
        gen_rel_field = config_cls.generic_relation_field_name
        for field in model_cls._meta.local_many_to_many:
            if field.name == gen_rel_field:
                model_cls._meta.local_many_to_many.remove(field)
                break
        try:
            delattr(model_cls, gen_rel_field)
        except AttributeError:
            pass
        
        if 'old_mgr' in cache:
            cache['old_mgr'].contribute_to_class(model_cls, 
                                                config_cls.manager_field_name)

        try:
            delattr(model_cls, config_cls.proxy_field_name)
        except AttributeError:
            pass

        if not manager_only:
            EavEntity.flush_attr_cache_for_model(model_cls)
            
        EavRegistry.cache.pop(cls_id)
        
     # todo : test cache
     # todo : tst unique identitfier  
     # todo:  test update attribute cache on attribute creation
     
post_save.connect(EavRegistry.update_attribute_cache, sender=EavAttribute)
post_delete.connect(EavRegistry.update_attribute_cache, sender=EavAttribute)
