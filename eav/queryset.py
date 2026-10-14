"""A custom :class:`EavQuerySet` that rewrites filters on EAV attributes.

It overrides relational operators and has pure functions for rewriting
Q-expressions. Q-expressions need to be rewritten for two reasons:

1. In order to hide implementation from the user and provide easy to use
   syntax sugar, i.e.::

       Supplier.objects.filter(eav__city__startswith='New')

   instead of::

       city_values = Value.objects.filter(value__text__startswith='New')
       Supplier.objects.filter(eav_values__in=city_values)

   For details see: :func:`eav_filter`.

2. To ensure that Q-expression tree is compiled to valid SQL.
   For details see: :func:`rewrite_q_expr`.

.. note:: EAV negation limitation

   Because EAV values are stored as individual rows in a shared table,
   using ``~Q(eav__attr=value)`` inside ``.filter()`` negates at the
   **row** level rather than the **entity** level.  This can produce
   unexpected results: an entity that has *other* EAV rows not matching
   the negation will still appear in the result set.

   The correct way to express "entities where attr A = x AND attr B ≠ y"
   is to chain ``.exclude()`` instead::

       # Wrong - row-level negation, may return unexpected results
       MyModel.objects.filter(Q(eav__a=x) & ~Q(eav__b=y))

       # Correct - entity-level negation
       MyModel.objects.filter(eav__a=x).exclude(eav__b=y)
"""

from functools import wraps

from django.db import transaction
from django.db.models import Q
from django.db.models.query import ModelIterable, QuerySet
from django.db.utils import NotSupportedError

from eav.logic.bulk import BulkValueWriter, chunked
from eav.logic.ordering import eav_order_slug, get_attribute, order_subquery
from eav.logic.schema import shared_schema_for
from eav.models import Attribute, EnumValue, Value


def is_eav_and_leaf(expr, gr_name):
    """
    Checks whether Q-expression is an EAV AND leaf.

    Args:
        expr (Union[Q, tuple]): Q-expression to be checked.
        gr_name (str): Generic relation attribute name, by default 'eav_values'

    Returns:
        bool
    """
    return (
        getattr(expr, "connector", None) == "AND"
        and len(expr.children) == 1
        and isinstance(expr.children[0], tuple)
        and expr.children[0][0] in ["pk__in", f"{gr_name}__in"]
    )


def rewrite_q_expr(model_cls, expr):
    """Rewrite a Q-expression to a safe form, so the generated SQL is valid.

    IGNORE:
        Suppose we have the following Q-expression:

        └── OR
             ├── AND
             │    └── eav_values__in [1, 2, 3]
             └── AND (1)
                  ├── AND
                  │    └── eav_values__in [4, 5]
                  └── AND
                       └── eav_values__in [6, 7, 8]
    IGNORE

        All EAV values are stored in a single table. Therefore, INNER JOIN
        generated for the AND-expression (1) will always fail, i.e.
        single row in a eav_values table cannot be both in two disjoint sets at
        the same time (and the whole point of using AND, usually, is two have
        two different sets). Therefore, we must partially rewrite the
        expression so that the generated SQL is valid.

    IGNORE:
        └── OR
             ├── AND
             │    └── eav_values__in [1, 2, 3]
             └── AND
                  └── pk__in [1, 2]
    IGNORE

        This is done by merging dangerous AND's and substituting them with
        explicit ``pk__in`` filter, where pks are taken from evaluated
        Q-expr branch.

    Args:
        model_cls: Model class used to construct a :class:`QuerySet` from a leaf
            attribute-value expression.
        expr: Q-expression (or attribute-value leaf) to be rewritten.

    Returns:
        The rewritten Q-expression or leaf.
    """
    # Node in a Q-expr can be a Q or an attribute-value tuple (leaf).
    # We are only interested in Qs.

    if isinstance(expr, Q):
        config_cls = getattr(model_cls, "_eav_config_cls", None)
        gr_name = config_cls.generic_relation_attr

        # Recursively check child nodes.
        expr.children = [rewrite_q_expr(model_cls, c) for c in expr.children]
        # Check which ones need a rewrite.
        rewritable = [c for c in expr.children if is_eav_and_leaf(c, gr_name)]

        # Conflict occurs only with two or more AND-expressions.
        # If there is only one we can ignore it.

        if len(rewritable) > 1:
            q = None
            # Save nodes which shouldn't be merged (non-EAV).
            other = [c for c in expr.children if c not in rewritable]

            for child in rewritable:
                if not (child.children and len(child.children) == 1):
                    raise AssertionError("Child must have exactly one descendant")
                # Child to be merged is always a terminal Q node,
                # i.e. it's an AND expression with attribute-value tuple child.
                attrval = child.children[0]
                if not isinstance(attrval, tuple):
                    raise TypeError("Attribute-value must be a tuple")

                fname = f"{gr_name}__in"

                # Child can be either a 'eav_values__in' or 'pk__in' query.
                # If it's the former then transform it into the latter.
                # Otherwise, check if the value is valid for the '__in' query.
                # If so, reverse it back to QuerySet so that set operators
                # can be applied.

                if attrval[0] == fname or hasattr(attrval[1], "__contains__"):
                    # Create model queryset.
                    leaf_qs = model_cls.objects.filter(**{fname: attrval[1]})
                else:
                    # Second val in tuple is a queryset.
                    leaf_qs = attrval[1]

                # Explicitly check for None. 'or' doesn't work here
                # as empty QuerySet, which is valid, is falsy.
                q = leaf_qs if q is None else q

                if expr.connector == "AND":
                    q &= leaf_qs
                else:
                    q |= leaf_qs

            # If any two children were merged,
            # update parent expression.
            if q is not None:
                expr.children = [*other, ("pk__in", q)]

    return expr


def eav_filter(func):
    """Decorate ``filter`` and ``exclude`` to rewrite EAV filters.

    Passes args through :func:`expand_q_filters` and kwargs through
    :func:`expand_eav_filter`. Returns the called function (filter or exclude).
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        nargs = []
        nkwargs = {}

        for arg in args:
            if isinstance(arg, Q):
                # Modify Q objects (warning: recursion ahead).
                arg = expand_q_filters(arg, self.model)  # noqa: PLW2901
                # Rewrite Q-expression to safeform.
                arg = rewrite_q_expr(self.model, arg)  # noqa: PLW2901
            nargs.append(arg)

        for key, value in kwargs.items():
            # Modify kwargs (warning: recursion ahead).
            nkey, nval = expand_eav_filter(self.model, key, value)

            if nkey in nkwargs:
                # Add filter to check if matching entity_id is
                # in the previous queryset with same nkey
                nkwargs[nkey] = nval.filter(
                    entity_id__in=nkwargs[nkey].values_list("entity_id", flat=True),
                ).distinct()
            else:
                nkwargs.update({nkey: nval})

        return func(self, *nargs, **nkwargs)

    return wrapper


def expand_q_filters(q, root_cls):
    """Rewrite the EAV filters of a Q object for the model *root_cls*.

    Recursively passes each filter / value in the Q object tree leaf nodes through
    :func:`expand_eav_filter`.
    """
    new_children = []

    for qi in q.children:
        if isinstance(qi, tuple):
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
    """Replace an EAV filter of *model_cls* with a subquery.

    Accepts a model class and a key, value, and recursively replaces any eav
    filter with a subquery.

    For example::

        key = 'eav__height'
        value = 5

    Would return::

        key = 'eav_values__in'
        value = Values.objects.filter(value_int=5, attribute__slug='height')
    """
    fields = key.split("__")
    config_cls = getattr(model_cls, "_eav_config_cls", None)

    if len(fields) > 1 and config_cls and fields[0] == config_cls.eav_attr:
        slug = fields[1]
        gr_name = config_cls.generic_relation_attr
        datatype = get_attribute(slug).datatype

        value_key = ""
        if datatype == Attribute.TYPE_ENUM and not isinstance(value, EnumValue):
            lookup = f"__value__{fields[2]}" if len(fields) > 2 else "__value"  # noqa: PLR2004
            value_key = f"value_{datatype}{lookup}"
        elif datatype == Attribute.TYPE_OBJECT:
            value_key = "generic_value_id"
        else:
            lookup = f"__{fields[2]}" if len(fields) > 2 else ""  # noqa: PLR2004
            value_key = f"value_{datatype}{lookup}"
        kwargs = {value_key: value, "attribute__slug": slug}
        value = Value.objects.filter(**kwargs)

        return f"{gr_name}__in", value

    # Not an eav field, so keep as is
    return key, value


class EavModelIterable(ModelIterable):
    """Yields model instances that share one lookup of their attributes."""

    def __iter__(self):
        """Yield the instances, pointing each entity at the shared schema."""
        schema = shared_schema_for(self.queryset.model)

        for instance in super().__iter__():
            if schema is not None:
                schema.attach(instance)
            yield instance


class EavQuerySet(QuerySet):
    """Overrides relational operators for EAV models."""

    def __init__(self, *args, **kwargs):
        """Evaluate into instances that share one attribute lookup."""
        super().__init__(*args, **kwargs)
        self._iterable_class = EavModelIterable

    @eav_filter
    def filter(self, *args, **kwargs):
        """Filter after passing the arguments through :func:`eav_filter`.

        The result is passed to the ``Manager`` filter method.
        """
        return super().filter(*args, **kwargs)

    @eav_filter
    def exclude(self, *args, **kwargs):
        """Exclude after passing the arguments through :func:`eav_filter`.

        The result is passed to the ``Manager`` exclude method.
        """
        return super().exclude(*args, **kwargs)

    @eav_filter
    def get(self, *args, **kwargs):
        """Get after passing the arguments through :func:`eav_filter`.

        The result is passed to the ``Manager`` get method.
        """
        return super().get(*args, **kwargs)

    def bulk_create(  # noqa: PLR0913, PLR0917
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,  # noqa: FBT002
        update_conflicts=False,  # noqa: FBT002
        update_fields=None,
        unique_fields=None,
    ):
        """
        Create *objs* and store the EAV values assigned to them.

        Assign values as for a single instance (``obj.eav.color = "red"``)
        before calling this. All instances are validated first, then created and
        their values written in batches of ``batch_size`` instances (1000 by
        default), about one query per 1000 rows, inside one transaction. Like
        Django's ``bulk_create`` this sends no signals, and the primary keys
        must be available afterwards (UUID keys, or a database that returns
        them).
        """
        objs = list(objs)
        writer = BulkValueWriter.for_objects(self.model, objs, batch_size)
        options = {
            "ignore_conflicts": ignore_conflicts,
            "update_conflicts": update_conflicts,
            "update_fields": update_fields,
            "unique_fields": unique_fields,
        }

        if writer is None:
            return super().bulk_create(objs, batch_size=batch_size, **options)

        if ignore_conflicts or update_conflicts:
            raise NotSupportedError(
                "bulk_create() cannot store EAV values together with conflict handling",
            )

        created = []
        with transaction.atomic(using=self.db):
            writer.validate_new(objs)

            for chunk in chunked(objs, writer.chunk_size):
                chunk_created = super().bulk_create(chunk, batch_size=batch_size)
                writer.write(chunk_created)
                created.extend(chunk_created)

        return created

    def bulk_update(self, objs, fields, batch_size=None):
        """
        Update *objs*, including EAV attributes named like ``eav__<slug>``.

        EAV attributes are written from the values assigned on each instance
        (``obj.eav.color = "red"``); instances without an assigned value for a
        listed attribute are left alone, and a value of ``None`` deletes it.
        Like Django's ``bulk_update`` this sends no signals.
        """
        objs = list(objs)
        eav_attr = self.model._eav_config_cls.eav_attr  # noqa: SLF001
        prefix = f"{eav_attr}__"
        eav_slugs = [
            name.removeprefix(prefix) for name in fields if name.startswith(prefix)
        ]
        model_fields = [name for name in fields if not name.startswith(prefix)]

        if not eav_slugs:
            return super().bulk_update(objs, fields, batch_size)

        if any(obj.pk is None for obj in objs):
            raise ValueError("All bulk_update() objects must have a primary key set.")

        writer = BulkValueWriter(self.model, batch_size)

        with transaction.atomic(using=self.db):
            updated = (
                super().bulk_update(objs, model_fields, batch_size)
                if model_fields
                else 0
            )
            writer.validate_assigned(objs, eav_slugs)

            for chunk in chunked(objs, writer.chunk_size):
                writer.write(chunk, eav_slugs)

        return updated

    def order_by(self, *fields):
        """Order by EAV attributes and regular fields.

        EAV attributes are named ``eav__<slug>``, optionally prefixed with ``-``.

        Each EAV attribute is annotated with a correlated subquery that reads
        the entity's value, so this works for integer and UUID primary keys,
        for empty querysets, and for any value type the database can sort.
        """
        config_cls = self.model._eav_config_cls  # noqa: SLF001
        queryset = self
        ordering = []

        for field in fields:
            slug = eav_order_slug(field, config_cls.eav_attr)

            if slug is None:
                ordering.append(field)
                continue

            alias = f"_eav_order_{slug}"
            if alias not in queryset.query.annotations:
                queryset = queryset.annotate(
                    **{alias: order_subquery(self.model, slug)},
                )
            ordering.append(f"-{alias}" if field.startswith("-") else alias)

        return QuerySet.order_by(queryset, *ordering)
