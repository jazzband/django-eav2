from django.db import models
from django.db.models import Q
#from django.db.models import Aggregate
from .models import EavAttribute

def expand_filter_string(q_str, root_cls):
    from .utils import EavRegistry
    extra_filters = {}
    # q_str is a filter argument, something like:
    # zoo__animal__food__eav__vitamin_c__gt, where
    # in this example 'food' would be registered as an entity,
    # 'eav' is the proxy field name, and 'contains_vitamin_c' is the
    # attribute.  So once we split the above example would be a list with
    # something we can easily process:
    # ['zoo','animal','food','eav','vitamin_c', 'gt']
    filter_tokens = q_str.split('__')
    current_cls = root_cls
    upperbound = len(filter_tokens) - 1
    i = 0
    while i < upperbound:
        current_cls_config = EavRegistry.get_config_cls_for_model(current_cls)
        if current_cls_config and filter_tokens[i] == current_cls_config.proxy_field_name:
            gr_field = current_cls_config.generic_relation_field_name
            # this will always work, because we're iterating over the length of the tokens - 1.
            # if someone just specifies 'zoo__animal_food__eav' as a filter,
            # they'll get the appropriate error: column 'eav' doesn't existt (i.e. if i != 0), 
            # prepend all the
            slug = filter_tokens[i + 1]
            datatype = EavAttribute.objects.get(slug=slug).datatype
            extra_filter_key = '%s__attribute__slug' % gr_field
            # if we're somewhere in the middle of this filter argument
            # joins up to this point
            if i != 0:
                extra_filter_key = '%s__%s' % ('__'.join(filter_tokens[0:i]), extra_filter_key)
            extra_filters[extra_filter_key] = slug
            # modify the filter argument in-place, expanding 'eav' into 'eav_values__value_<datatype>'
            filter_tokens = filter_tokens[0:i] + [gr_field, 'value_%s' % datatype] + filter_tokens[i + 2:]
            # this involves a little indexing voodoo, because we inserted two elements in place of one
            # original element
            i += 1
            upperbound += 1
#            filter_tokens[0] = "%s__value_%s" % (gr_field, datatype)
        else:
            direct = False
            # Is it not EAV, but also not another field?
            try:
                field_object, model, direct, m2m = current_cls._meta.get_field_by_name(filter_tokens[0])
                # If we've hit the end, i.e. a simple column attribute like IntegerField or Boolean Field,
                # we're done modifying the tokens, so we can break out of the loop early
                if direct:
                    return '__'.join(filter_tokens), extra_filters
                else:
                # It is a foreign key to some other model, so we need to keep iterating, looking for registered
                # entity models to expand
                    current_cls = field_object.model
            except models.FieldDoesNotExist:
                # this is a bogus filter anyway on a non-existent attribute, let the call to the super filter throw the 
                # appropriate error
                return '__'.join(filter_tokens), extra_filters

        # regular loop forward
        i += 1
    # at the end of the day, we return the modified keyword filter, and any additional filters needed to make this
    # query work, for passing up to the super call to filter()
    return '__'.join(filter_tokens), extra_filters

def expand_q_filters(q, root_cls):
    new_children = []
    for qi in q.children:
        if type(qi) is tuple:
            # this child is a leaf node: in Q this is a 2-tuple of:
            # (filter parameter, value)
            expanded_string, extra_filters = expand_filter_string(qi[0], root_cls)
            extra_filters.update({expanded_string: qi[1]})
            if q.connector == 'OR':
                # if it's an or, we now have additional filters that need
                # to be ANDed together, so we have to make a sub-Q child
                # in place of the original tuple
                new_children.append(Q(**extra_filters))
            else:
                # otherwise, we can just append all the new filters, they're
                # ANDed together anyway
                for k,v in extra_filters.items():
                    new_children.append((k,v))
        else:
            # this child is another Q node: recursify!
            new_children.append(expand_q_filters(qi, root_cls))
    q.children = new_children
    return q

class EntityManager(models.Manager):
    def filter(self, *args, **kwargs):
        cls = self.model
        for arg in args:
            if isinstance(arg, Q):
                # modify Q objects in-place (warning: recursion ahead)
                expand_q_filters(arg, cls)
        qs = self.get_query_set().filter(*args)
        for lookup, value in kwargs.items():
            updated_lookup, extra_filters = expand_filter_string(lookup, cls)
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
