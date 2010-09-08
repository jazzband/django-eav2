from django.db import models
#from django.db.models import Aggregate
from .models import EavAttribute


def expand_filter_string(model_cls, q_str, prefix='', extra_filters=None):
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
        extra_filter_key = '%s__attribute__slug' % gr_field
        if prefix:
            extra_filter_key = '%s__%s' % (prefix, extra_filter_key)
        extra_filters[extra_filter_key] = slug
        fields[0] = "%s__value_%s" % (gr_field, datatype)
        fields.pop(1)
        return '__'.join(fields), extra_filters


    direct = False
    # Is it not EAV, but also not another field?
    try:
        field_object, model, direct, m2m = model_cls._meta.get_field_by_name(fields[0])
    except models.FieldDoesNotExist:
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

class EntityManager(models.Manager):
    def filter(self, *args, **kwargs):
        qs = self.get_query_set().filter(*args)
        cls = self.model
        for lookup, value in kwargs.items():
            updated_lookup, extra_filters = expand_filter_string(cls, lookup)
            extra_filters.update({updated_lookup: value})
            qs = qs.filter(**extra_filters)
        return qs

    def exclude(self, *args, **kwargs):
        qs = self.get_query_set().exclude(*args)
        cls = self.model
        for lookup, value in kwargs.items():
            lookups = self._filter_by_lookup(qs, lookup, value)
            updated_lookup, extra_filters = expand_filter_string(cls, lookup)
            extra_filters.update({updated_lookup: value})
            qs = qs.exclude(**lookups)
        return qs
    '''
    def aggregate(self, *args, **kwargs):
        #import ipdb; ipdb.set_trace()
        cls = self.model
        for arg in args:
            kwargs.update({arg.default_alias: arg})
        args = ()
        print kwargs
        filters = {}
        aggs = []
        for key, value in kwargs.items():
            updated_lookup, extra_filters = expand_filter_string(cls, value.lookup)
            agg = Aggregate(updated_lookup)
            #agg.default_alias=key
            agg.name=value.name
            aggs.append(agg)
            filters.update(extra_filters)
        qs = self.get_query_set().filter(**filters)
        return qs.aggregate(*aggs)
    '''
