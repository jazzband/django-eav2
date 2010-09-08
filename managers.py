from django.db import models
from .models import EavAttribute



class EntityManager(models.Manager):
    def expand_filter_string(self, model_cls, q_str, prefix='', extra_filters=None):
        from .utils import EavRegistry
        if not extra_filters:
            extra_filters = {}
        fields = q_str.split('__')

        # Is it EAV?
        config_cls = EavRegistry.get_config_cls_for_model(model_cls)
        if len(fields) > 1 and config_cls and fields[0] == config_cls.proxy_field_name:
            gr_field = config_cls.generic_relation_field_name
            slug = fields[1]
            datatype = EavAttribute.objects.get(slug=slug).datatype
            extra_filter_key = '%s__%s__attribute__slug' % (prefix, gr_field)
            extra_filters[extra_filter_key] = slug
            fields[0] = "%s__value_%s" % (gr_field, datatype)
            fields.pop(1)
            return '__'.join(fields), extra_filters

        # Is it not EAV, but also not another field?
        try:
            field_object, model, direct, m2m = model_cls._meta.get_field_by_name(fields[0])
        except FieldDoesNotExist:
            return q_str, extra_filters

        # Is it a direct field?
        if direct:
            return q_str, extra_filters
        else:
        # It is a foreign key.
            prefix = "%s__%s" % (prefix, fields[0]) if prefix else fields[0]
            sub_q_str = '__'.join(fields[1:])
            retstring, dictionary = self.expand_filter_string(field_object.model, sub_q_str, prefix, extra_filters)
            return ("%s__%s" % (fields[0], retstring), dictionary)

    def filter(self, *args, **kwargs):
        qs = self.get_query_set().filter(*args)
        cls = self.model
        for lookup, value in kwargs.items():
            updated_lookup, extra_filters = self.expand_filter_string(cls, lookup)
            extra_filters.update({updated_lookup: value})
            qs = qs.filter(**extra_filters)
        return qs

    def exclude(self, *args, **kwargs):
        qs = self.get_query_set().exclude(*args)
        for lookup, value in kwargs.items():
            lookups = self._filter_by_lookup(qs, lookup, value)
            updated_lookup, extra_filters = self.expand_filter_string(cls, lookup)
            extra_filters.update({updated_lookup: value})
            qs = qs.exclude(**lookups)
        return qs
