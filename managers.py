from functools import wraps

from django.db import models

from .models import EavAttribute, EavValue

def eav_filter(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        new_args = []
        for arg in args:
            if isinstance(arg, models.Q):
                # modify Q objects (warning: recursion ahead)
                new_args.append(expand_q_filters(arg, self.model))

        new_kwargs = {}
        for key, value in kwargs.items():
            new_key, new_value = expand_eav_filter(self.model, key, value)
            new_kwargs.update({new_key: new_value})

        return func(self, *new_args, **new_kwargs).distinct()
    return wrapper


def expand_q_filters(q, root_cls):
    new_children = []
    for qi in q.children:
        if type(qi) is tuple:
            # this child is a leaf node: in Q this is a 2-tuple of:
            # (filter parameter, value)
            key, value = expand_eav_filter(root_cls, *qi)
            new_children.append(models.Q(**{key: value}))
        else:
            # this child is another Q node: recursify!
            new_children.append(expand_q_filters(qi, root_cls))
    q.children = new_children
    return q


def expand_eav_filter(model_cls, key, value):
    from .utils import EavRegistry
    fields = key.split('__')

    config_cls = EavRegistry.get_config_cls_for_model(model_cls)
    if len(fields) > 1 and config_cls and \
       fields[0] == config_cls.proxy_field_name:
        slug = fields[1]
        gr_name = config_cls.generic_relation_field_name
        datatype = EavAttribute.objects.get(slug=slug).datatype

        lookup = '__%s' % fields[2] if len(fields) > 2 else ''
        kwargs = {'value_%s%s' % (datatype, lookup): value,
                  'attribute__slug': slug}
        value = EavValue.objects.filter(**kwargs)

        return '%s__in' % gr_name, value

    try:
        field, m, direct, m2m = model_cls._meta.get_field_by_name(fields[0])
    except models.FieldDoesNotExist:
        return key, value

    if direct:
        return key, value
    else:
        sub_key = '__'.join(fields[1:])
        key, value = expand_eav_filter(field.model, sub_key, value)
        return '%s__%s' % (fields[0], key), value


class EntityManager(models.Manager):
    @eav_filter
    def filter(self, *args, **kwargs):
        return super(EntityManager, self).filter(*args, **kwargs)

    @eav_filter
    def exclude(self, *args, **kwargs):
        return super(EntityManager, self).exclude(*args, **kwargs)
