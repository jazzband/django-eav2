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

from django.db.utils import DatabaseError
from django.db.models.signals import pre_init, post_init, pre_save, post_save
from django.contrib.contenttypes import generic

from .managers import EntityManager
from .models import Entity, Attribute, Value


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
    @staticmethod
    def register(model_cls, config_cls=None):
        if hasattr(model_cls, '_eav_config_cls'):
            return

        if config_cls is EavConfig or config_cls is None:
            config_cls = type("%sConfig" % model_cls.__name__,
                              (EavConfig,), {})

        # set _eav_config_cls on the model so we can access it there
        setattr(model_cls, '_eav_config_cls', config_cls)

        reg = Registry(model_cls)
        reg._register_self()

    @staticmethod
    def unregister(model_cls):
        if not getattr(model_cls, '_eav_config_cls', None):
            return
        reg = Registry(model_cls)
        reg._unregister_self()

        delattr(model_cls, '_eav_config_cls')
        

    @staticmethod
    def attach_eav_attr(sender, *args, **kwargs):
        '''
        Attache EAV Entity toolkit to an instance after init.
        '''
        instance = kwargs['instance']
        config_cls = instance.__class__._eav_config_cls
        setattr(instance, config_cls.eav_attr, Entity(instance))

    def __init__(self, model_cls):
        self.model_cls = model_cls
        self.config_cls = model_cls._eav_config_cls

    def _attach_manager(self):
        # save the old manager if the attribute name conflict with the new one
        if hasattr(self.model_cls, self.config_cls.manager_attr):
            mgr = getattr(self.model_cls, self.config_cls.manager_attr)
            self.config_cls.old_mgr = mgr

        # attache the new manager to the model
        mgr = EntityManager()
        mgr.contribute_to_class(self.model_cls, self.config_cls.manager_attr)

    def _detach_manager(self):
        delattr(self.model_cls, self.config_cls.manager_attr)
        if hasattr(self.config_cls, 'old_mgr'):
            self.config_cls.old_mgr \
                .contribute_to_class(self.model_cls,
                                     self.config_cls.manager_attr)

    def _attach_signals(self):
        post_init.connect(Registry.attach_eav_attr, sender=self.model_cls)
        pre_save.connect(Entity.pre_save_handler, sender=self.model_cls)
        post_save.connect(Entity.post_save_handler, sender=self.model_cls)

    def _detach_signals(self):
        post_init.disconnect(Registry.attach_eav_attr, sender=self.model_cls)
        pre_save.disconnect(Entity.pre_save_handler, sender=self.model_cls)
        post_save.disconnect(Entity.post_save_handler, sender=self.model_cls)

    def _attach_generic_relation(self):
        rel_name = self.config_cls.generic_relation_related_name or \
                   self.model_cls.__name__

        gr_name = self.config_cls.generic_relation_attr.lower()
        generic_relation = \
                     generic.GenericRelation(Value,
                                             object_id_field='entity_id',
                                             content_type_field='entity_ct',
                                             related_name=rel_name)
        generic_relation.contribute_to_class(self.model_cls, gr_name)


    def _detach_generic_relation(self):
        gen_rel_field = self.config_cls.generic_relation_attr
        for field in self.model_cls._meta.local_many_to_many:
            if field.name == gen_rel_field:
                self.model_cls._meta.local_many_to_many.remove(field)
                break
        try:
            delattr(self.model_cls, gen_rel_field)
        except AttributeError:
            pass

    def _register_self(self):
        self._attach_manager()

        if not self.config_cls.manager_only:
            self._attach_signals()
            self._attach_generic_relation()

    def _unregister_self(self):
        self._detach_manager()

        if not self.config_cls.manager_only:
            self._detach_signals()
            self._detach_generic_relation()
