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
from django.db.models.signals import pre_init, post_init, pre_save, post_save
from .managers import EntityManager
from .models import (Entity, Attribute, Value, 
                     get_unique_class_identifier)


class EavConfig(Entity):

    manager_attr ='objects'
    manager_only = False
    eav_attr = 'eav'
    generic_relation_attr = 'eav_values'
    generic_relation_related_name = None

    @classmethod
    def get_attributes(cls):
        """
             By default, all attributes apply to an entity,
             unless otherwise specified.
        """
        return Attribute.objects.all()
        

class Registry(object):
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

        if cls_id in Registry.cache:
            return Registry.cache[cls_id]['config_cls']


    @staticmethod
    def attach_eav_attr(sender, *args, **kwargs):
        '''
        Attache EAV Entity toolkit to an instance after init.
        '''
        instance = kwargs['instance']
        config_cls = Registry.get_config_cls_for_model(sender)
        setattr(instance, config_cls.eav_attr, Entity(instance))

    @staticmethod
    def attach_manager(model_cls):
        cls_id = get_unique_class_identifier(model_cls)
        config_cls = model_cls._eav_config_cls
        # save the old manager if the attribute name conflict with the new one
        if hasattr(model_cls, config_cls.manager_attr):
            mgr = getattr(model_cls, config_cls.manager_attr)
            Registry.cache[cls_id]['old_mgr'] = mgr

        # attache the new manager to the model
        mgr = EntityManager()
        mgr.contribute_to_class(model_cls, config_cls.manager_attr)

    @staticmethod
    def detach_manager(model_cls):
        cls_id = get_unique_class_identifier(model_cls)
        config_cls = model_cls._eav_config_cls

        try:
            delattr(model_cls, config_cls.manager_attr)
        except AttributeError:
            pass
        
        if 'old_mgr' in Registry.cache[cls_id]:
            Registry.cache[cls_id]['old_mgr'] \
                    .contribute_to_class(model_cls, config_cls.manager_attr)


    @staticmethod
    def attach_signals(model_cls):
        post_init.connect(Registry.attach_eav_attr, sender=model_cls)
        pre_save.connect(Entity.pre_save_handler, sender=model_cls)
        post_save.connect(Entity.post_save_handler, sender=model_cls)


    @staticmethod
    def detach_signals(model_cls):
        post_init.disconnect(Registry.attach_eav_attr, sender=model_cls)
        pre_save.disconnect(Entity.pre_save_handler, sender=model_cls)
        post_save.disconnect(Entity.post_save_handler, sender=model_cls)

    @staticmethod
    def attach_generic_relation(model_cls):
        config_cls = model_cls._eav_config_cls
        if config_cls.generic_relation_related_name:
            rel_name = config_cls.generic_relation_related_name
        else:
            rel_name = model_cls.__name__
        gr_name = config_cls.generic_relation_attr.lower()
        generic_relation = \
                     generic.GenericRelation(Value,
                                             object_id_field='entity_id',
                                             content_type_field='entity_ct',
                                             related_name=rel_name)
        generic_relation.contribute_to_class(model_cls, gr_name)

    @staticmethod
    def detach_generic_relation(model_cls):
        config_cls = model_cls._eav_config_cls

        gen_rel_field = config_cls.generic_relation_attr
        for field in model_cls._meta.local_many_to_many:
            if field.name == gen_rel_field:
                model_cls._meta.local_many_to_many.remove(field)
                break
        try:
            delattr(model_cls, gen_rel_field)
        except AttributeError:
            pass

 
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
    def register(model_cls, config_cls=EavConfig):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        
        cls_id = get_unique_class_identifier(model_cls)

        # Don't allow multiple registrations
        if cls_id in Registry.cache:
            return

        config_cls = Registry.wrap_config_class(model_cls, config_cls)

        # set _eav_config_cls on the model so we can access it there
        setattr(model_cls, '_eav_config_cls', config_cls)

        Registry.cache[cls_id] = {'config_cls': config_cls,
                                  'model_cls': model_cls}

        Registry.attach_manager(model_cls)

        if not config_cls.manager_only:
            Registry.attach_signals(model_cls)   
            Registry.attach_generic_relation(model_cls)

    @staticmethod
    def unregister(model_cls):
        """
            Do the INVERSE of 'Inject eav features into the given model 
            and attach a signal listener to it for setup.'
        """
        cls_id = get_unique_class_identifier(model_cls)
        
        if not cls_id in Registry.cache:
            return

        cache = Registry.cache[cls_id]
        config_cls = cache['config_cls']
        manager_only = cache['config_cls'].manager_only

        Registry.detach_manager(model_cls)

        if not config_cls.manager_only:
            Registry.detach_signals(model_cls)
            Registry.detach_generic_relation(model_cls)

        try:
            delattr(model_cls, '_eav_config_cls')
        except AttributeError:
            pass
            
        Registry.cache.pop(cls_id)
