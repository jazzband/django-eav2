'''
Queryset module.

This module contains custom EavQuerySet class used for overriding
relational operators and pure functions for rewriting Q-expressions.
Q-expressions need to be rewritten for two reasons:

    1. In order to hide implementation from the user and provide easy to use
       syntax sugar, i.e.::

           Supplier.objects.filter(eav__city__startswith='New')

       instead of::

           city_values = Value.objects.filter(value__text__startswith='New')
           Supplier.objects.filter(eav_values__in=city_values)

       For details see: ``eav_filter``.

    2. To ensure that Q-expression tree is compiled to valid SQL.
       For details see: ``rewrite_q_expr``.
'''

import sys
from functools import reduce, wraps

from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet

from .models import Attribute, Value


def is_eav_and_leaf(expr, gr_name):
    '''
    Checks whether Q-expression is an EAV AND leaf.

    Args:
        expr (Q | tuple): Q-expression to be checked.
        gr_name (str): Generic relation attribute name, by default 'eav_values'

    Returns:
        bool
    '''
    return (getattr(expr, 'connector', None) == 'AND' and
            len(expr.children) == 1 and
            expr.children[0][0] in ['pk__in', '{}__in'.format(gr_name)])


def rewrite_q_expr(model_cls, expr):
    '''
    Rewrites Q-expression to safe form, in order to ensure that
    generated SQL is valid.

    Suppose we have the following Q-expression:

    └── OR
         ├── AND
         │    └── eav_values__in [1, 2, 3]
         └── AND (1)
              ├── AND
              │    └── eav_values__in [4, 5]
              └── AND
                   └── eav_values__in [6, 7, 8]

    All EAV values are stored in a single table. Therefore, INNER JOIN
    generated for the AND-expression (1) will always fail, i.e.
    single row in a eav_values table cannot be both in two disjoint sets at
    the same time (and the whole point of using AND, usually, is two have
    two different sets). Therefore, we must paritially rewrite the
    expression so that the generated SQL is valid::

    └── OR
         ├── AND
         │    └── eav_values__in [1, 2, 3]
         └── AND
              └── pk__in [1, 2]

    This is done by merging dangerous AND's and substituting them with
    explicit ``pk__in`` filter, where pks are taken from evaluted
    Q-expr branch.

    Args:
        model_cls (Model class): model class used to construct QuerySet
        from leaf attribute-value expression.
        expr: (Q | tuple): Q-expression (or attr-val leaf) to be rewritten.

    Returns:
        Q | tuple
    '''
    # Node in a Q-expr can be a Q or an attribute-value tuple (leaf).
    # We are only interested in Qs.

    if type(expr) == Q:
        config_cls = getattr(model_cls, '_eav_config_cls', None)
        assert config_cls
        gr_name = config_cls.generic_relation_attr

        # Recurively check child nodes.
        expr.children = [rewrite_q_expr(model_cls, c) for c in expr.children]
        # Check which ones need a rewrite.
        rewritable = [c for c in expr.children if is_eav_and_leaf(c, gr_name)]

        # Conflict occurs only with two or more AND-expressions.
        # If there is only one we can ignore it.

        if len(rewritable) > 1:
            q = None
            # Save nodes which shouldn't be merged (non-EAV).
            other = [c for c in expr.children if not c in rewritable]

            for child in rewritable:
                assert child.children and len(child.children) == 1
                # Child to be merged is always a terminal Q node,
                # i.e. it's an AND expression with attribute-value tuple child.
                attrval = child.children[0]
                assert type(attrval) == tuple

                fname = '{}__in'.format(gr_name)

                # Child can be either a 'eav_values__in' or 'pk__in' query.
                # If it's the former then transform it into the latter.
                # Otherwise, check if the value is valid for the '__in' query.
                # If so, reverse it back to QuerySet so that set operators
                # can be applied.

                if attrval[0] == fname or hasattr(attrval[1], '__contains__'):
                    # Create model queryset.
                    _q = model_cls.objects.filter(**{fname: attrval[1]})
                else:
                    # Second val in tuple is a queryset.
                    _q = attrval[1]

                # Explicitly check for None. 'or' doesn't work here
                # as empty QuerySet, which is valid, is falsy.
                q = q if q != None else _q

                if expr.connector == 'AND':
                    q &= _q
                else:
                    q |= _q

            # If any two children were merged,
            # update parent expression.
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
            if isinstance(arg, Q):
                # Modify Q objects (warning: recursion ahead).
                arg = expand_q_filters(arg, self.model)
                # Rewrite Q-expression to safeform.
                arg = rewrite_q_expr(self.model, arg)
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
    Recursively passes each filter / value in the Q object tree leaf nodes
    through expand_eav_filter
    '''
    new_children = []

    for qi in q.children:
        if type(qi) is tuple:
            # This child is a leaf node: in Q this is a 2-tuple of:
            # (filter parameter, value).
            key, value = expand_eav_filter(root_cls, *qi)
            new_children.append(Q(**{key: value}))
        else:
            # This child is another Q node: recursify!
            new_children.append(expand_q_filters(qi, root_cls))

    q.children = new_children
    return q


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

    if len(fields) > 1 and config_cls and fields[0] == config_cls.eav_attr:
        slug = fields[1]
        gr_name = config_cls.generic_relation_attr
        datatype = Attribute.objects.get(slug=slug).datatype

        lookup = '__%s' % fields[2] if len(fields) > 2 else ''
        kwargs = {
            'value_{}{}'.format(datatype, lookup): value,
            'attribute__slug': slug
        }
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
        return '{}__{}'.format(ields[0], key), value


class EavQuerySet(QuerySet):
    '''
    Overrides relational operators for EAV models.
    '''

    @eav_filter
    def filter(self, *args, **kwargs):
        '''
        Pass *args* and *kwargs* through ``eav_filter``, then pass to
        the ``models.Manager`` filter method.
        '''
        return super().filter(*args, **kwargs).distinct()

    @eav_filter
    def exclude(self, *args, **kwargs):
        '''
        Pass *args* and *kwargs* through ``eav_filter``, then pass to
        the ``models.Manager`` exclude method.
        '''
        return super().exclude(*args, **kwargs).distinct()

    @eav_filter
    def get(self, *args, **kwargs):
        '''
        Pass *args* and *kwargs* through ``eav_filter``, then pass to
        the ``models.Manager`` get method.
        '''
        return super().get(*args, **kwargs)
