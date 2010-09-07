from django.db import models

class EntityManager(models.Manager):
    def filter(self, *args, **kwargs):
        qs = self.get_query_set().filter(*args)
        for lookup, value in kwargs.items():
            lookups = self._filter_by_lookup(qs, lookup, value)
            qs = qs.filter(**lookups)
        return qs

    def _filter_by_lookup(self, qs, lookup, value):
        eav_entity = self._get_eav_entity()
        slugs = eav_entity.get_all_attribute_slugs()
        cache = eav_entity.get_attr_cache()
        fields = self.model._meta.get_all_field_names()
        attributes = eav_entity.get_all_attributes()

        config_cls = self._get_config_cls()
        eav_prefix = config_cls.proxy_field_name
        gr_name = config_cls.generic_relation_field_name

        if not lookup.startswith("%s__" % eav_prefix):
            return {lookup: value}

        lookup = lookup.lstrip("%s__" % eav_prefix)        

        # Sublookup will be None if there is no __ in the lookup
        name, sublookup = (lookup.split('__', 1) + [None])[:2]

        if name in slugs:
            # EAV attribute (Attr instance linked to entity)
            attribute = eav_entity.get_attribute_by_slug(name)
            return self._filter_by_simple_schema(qs, lookup, sublookup, value, attribute)
        else:
            raise NameError('Cannot filter items by attributes: unknown '
                            'attribute "%s". Available fields: %s. '
                            'Available attribute: %s.' % (name,
                            ', '.join(fields), ', '.join(slugs)))

    def _filter_by_simple_schema(self, qs, lookup, sublookup, value, attribute):
        config_cls = self._get_config_cls()
        eav_prefix = config_cls.proxy_field_name
        gr_name = config_cls.generic_relation_field_name
          

        value_lookup = '%s__value_%s' % (gr_name, attribute.datatype)
        if sublookup:
            value_lookup = '%s__%s' % (value_lookup, sublookup)
        return { value_lookup: value }

    def _get_config_cls(self):
        from .utils import EavRegistry
        return EavRegistry.get_config_cls_for_model(self.model)

    def _get_eav_entity(self):
        cls = self._get_config_cls()
        eav_entity_name = cls.proxy_field_name
        return getattr(self.model, eav_entity_name)
