import sys
from functools import reduce, wraps

from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet

from .models import Attribute, Value


def register_eav(**kwargs):
    '''
    Registers the given model(s) classes and wrapped Model class with
    django-eav:

    @register_eav
    class Author(models.Model):
        pass
    '''
    from . import register
    from django.db.models import Model

    def _model_eav_wrapper(model_class):
        if not issubclass(model_class, Model):
            raise ValueError('Wrapped class must subclass Model.')
        register(model_class, **kwargs)
        return model_class

    return _model_eav_wrapper


def is_rewritable(expr):
    '''
    Checks whether Q-expression should be rewritten to safe form.
    '''
    return (getattr(expr, 'connector', None) == 'AND' and
            len(expr.children) == 1 and
            expr.children[0][0] in ['pk__in', 'eav_values__in'])


def rewrite_q_expr(manager, expr):
    # Expression can be a Q or an attribute-value tuple.
    if type(expr) == Q:
        expr.children = [rewrite_q_expr(manager, c) for c in expr.children]
        rewritable = [c for c in expr.children if is_rewritable(c)]

        if len(rewritable) > 1:
            q = None
            other = [c for c in expr.children if not c in rewritable]

            for child in rewritable:
                child = child.children[0]

                if child[0] == 'eav_values__in':
                    _q = manager.model.objects.filter(eav_values__in=child[1])
                    q = q if q != None else _q

                    if expr.connector == 'AND':
                        q = q & _q
                    else:
                        q = q | _q
                else:
                    _q = child[1]
                    q = q if q != None else _q

                    if expr.connector == 'AND':
                        q = q & _q
                    else:
                        q = q | _q

            if q != None:
                expr.children = other + [('pk__in', q)]

    return expr


def eav_filter(func):
    '''
    Decorator used to wrap filter and exclude methods. Passes args through
    expand_q_filters and kwargs through expand_eav_filter. Returns the
    called function (filter or exclude).
    '''

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        nargs = []
        nkwargs = {}

        for arg in args:
            if isinstance(arg, models.Q):
                # Modify Q objects (warning: recursion ahead).
                arg = expand_q_filters(arg, self.model)
                arg = rewrite_q_expr(self, arg)
            nargs.append(arg)

        for key, value in kwargs.items():
            # Modify kwargs (warning: recursion ahead).
            nkey, nval = expand_eav_filter(self.model, key, value)

            if nkey in nkwargs:
                # Apply AND to both querysets.
                nkwargs[nkey] = (nkwargs[nkey] & nval).distinct()
            else:
                nkwargs.update({nkey: nval})

        return func(self, *nargs, **nkwargs)

    return wrapper


def expand_q_filters(q, root_cls):
    '''
    Takes a Q object and a model class.
    Recursivley passes each filter / value in the Q object tree leaf nodes
    through expand_eav_filter
    '''
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

    _q = models.Q()
    _q.children = new_children
    _q.connector = q.connector
    _q.negated = q.negated
    return _q


def expand_eav_filter(model_cls, key, value):
    '''
    Accepts a model class and a key, value.
    Recurisively replaces any eav filter with a subquery.

    For example::

        key = 'eav__height'
        value = 5

    Would return::

        key = 'eav_values__in'
        value = Values.objects.filter(value_int=5, attribute__slug='height')
    '''
    fields = key.split('__')
    config_cls = getattr(model_cls, '_eav_config_cls', None)

    if len(fields) > 1 and config_cls and \
       fields[0] == config_cls.eav_attr:
        slug = fields[1]
        gr_name = config_cls.generic_relation_attr
        datatype = Attribute.objects.get(slug=slug).datatype

        lookup = '__%s' % fields[2] if len(fields) > 2 else ''
        kwargs = {'value_%s%s' % (datatype, lookup): value,
                  'attribute__slug': slug}
        value = Value.objects.filter(**kwargs)

        return '%s__in' % gr_name, value

    try:
        field = model_cls._meta.get_field(fields[0])
    except models.FieldDoesNotExist:
        return key, value

    if not field.auto_created or field.concrete:
        return key, value
    else:
        sub_key = '__'.join(fields[1:])
        key, value = expand_eav_filter(field.model, sub_key, value)
        return '%s__%s' % (fields[0], key), value
