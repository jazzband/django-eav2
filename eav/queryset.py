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
   using ``~models.Q(eav__attr=value)`` inside ``.filter()`` negates at the
   **row** level rather than the **entity** level.  This can produce
   unexpected results: an entity that has *other* EAV rows not matching
   the negation will still appear in the result set.

   The correct way to express "entities where attr A = x AND attr B ≠ y"
   is to chain ``.exclude()`` instead::

       # Wrong - row-level negation, may return unexpected results
       MyModel.objects.filter(models.Q(eav__a=x) & ~models.Q(eav__b=y))

       # Correct - entity-level negation
       MyModel.objects.filter(eav__a=x).exclude(eav__b=y)
"""

from __future__ import annotations

import operator
from functools import reduce, wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast

from django.db import models, transaction
from django.db.models.query import ModelIterable, QuerySet
from django.db.utils import NotSupportedError

from eav.logic.bulk import BulkValueWriter, chunked, split_eav_fields
from eav.logic.entities import config_of
from eav.logic.entity_pk import get_entity_pk_type
from eav.logic.lookups import leaf_queryset, value_lookup
from eav.logic.ordering import eav_order_slug, get_attribute, order_subquery
from eav.logic.schema import shared_schema_for
from eav.models import Value

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Iterator

    from typing_extensions import Self

_ModelT = TypeVar("_ModelT", bound=models.Model)
_FuncT = TypeVar("_FuncT", bound="Callable[..., Any]")


def is_eav_and_leaf(expr: Any, gr_name: str) -> bool:
    """
    Check whether Q-expression is an EAV AND leaf.

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


def rewrite_q_expr(
    model_cls: Any,
    expr: models.Q | tuple[str, Any],
) -> models.Q | tuple[str, Any]:
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
    if not isinstance(expr, models.Q):
        return expr

    gr_name = model_cls._eav_config_cls.generic_relation_attr  # noqa: SLF001

    # Recursively check child nodes.
    children: list[Any] = [
        rewrite_q_expr(model_cls, cast("models.Q", child)) for child in expr.children
    ]
    leaves = [child for child in children if is_eav_and_leaf(child, gr_name)]

    # Conflict occurs only with two or more AND-expressions.
    # If there is only one we can ignore it.
    if len(leaves) > 1:
        # Each leaf is a terminal Q node, i.e. an AND expression with a single
        # attribute-value tuple child.
        in_name = f"{gr_name}__in"
        querysets = [
            leaf_queryset(model_cls, leaf.children[0], in_name) for leaf in leaves
        ]
        merge = operator.and_ if expr.connector == "AND" else operator.or_

        # Keep the nodes that shouldn't be merged (non-EAV).
        others = [child for child in children if child not in leaves]
        children = [*others, ("pk__in", reduce(merge, querysets))]

    expr.children = children
    return expr


def eav_filter(func: _FuncT) -> _FuncT:
    """Decorate ``filter`` and ``exclude`` to rewrite EAV filters.

    Passes args through :func:`expand_q_filters` and kwargs through
    :func:`expand_eav_filter`. Returns the called function (filter or exclude).
    """

    @wraps(func)
    def wrapper(self: EavQuerySet[Any], *args: Any, **kwargs: Any) -> Any:
        # Modify Q objects (warning: recursion ahead) and rewrite them to a safe form.
        rewritten = [
            rewrite_q_expr(self.model, expand_q_filters(arg, self.model))
            if isinstance(arg, models.Q)
            else arg
            for arg in args
        ]
        filters: dict[str, Any] = {}
        pk_field = get_entity_pk_type(self.model)

        for key, raw_value in kwargs.items():
            # Modify kwargs (warning: recursion ahead).
            name, operand = expand_eav_filter(self.model, key, raw_value)
            previous = filters.get(name)

            # Add filter to check if the matching entity is in the previous
            # queryset with same name.
            filters[name] = (
                operand
                if previous is None
                else operand.filter(
                    **{f"{pk_field}__in": previous.values_list(pk_field, flat=True)},
                ).distinct()
            )

        return func(self, *rewritten, **filters)

    return cast("_FuncT", wrapper)


def expand_q_filters(query: models.Q, root_cls: Any) -> models.Q:
    """Rewrite the EAV filters of a Q object for the model *root_cls*.

    Recursively passes each filter / value in the Q object tree leaf nodes through
    :func:`expand_eav_filter`.
    """
    new_children: list[Any] = []

    for child in query.children:
        if isinstance(child, tuple):
            # This child is a leaf node: in Q this is a 2-tuple of:
            # (filter parameter, value).
            key, operand = expand_eav_filter(root_cls, *child)
            new_children.append(models.Q(**{key: operand}))
        else:
            # This child is another Q node: recursify!
            new_children.append(expand_q_filters(cast("models.Q", child), root_cls))

    query.children = new_children
    return query


def expand_eav_filter(model_cls: Any, key: str, raw_value: Any) -> tuple[str, Any]:
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
        datatype = get_attribute(slug).datatype
        extra = fields[2] if len(fields) > 2 else None  # noqa: PLR2004
        lookup = value_lookup(datatype, raw_value, extra)
        subquery = Value.objects.filter(**{lookup: raw_value, "attribute__slug": slug})

        return f"{config_cls.generic_relation_attr}__in", subquery

    # Not an eav field, so keep as is
    return key, raw_value


class EavModelIterable(ModelIterable):  # type: ignore[type-arg]
    """An iterable of model instances that share one lookup of their attributes."""

    def __iter__(self) -> Iterator[Any]:
        """Yield the instances, pointing each entity at the shared schema."""
        schema = shared_schema_for(self.queryset.model)

        for instance in super().__iter__():
            if schema is not None:
                schema.attach(instance)
            yield instance


class EavQuerySet(QuerySet[_ModelT]):
    """A queryset of EAV models that understands ``eav__<slug>`` lookups."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Evaluate into instances that share one attribute lookup."""
        super().__init__(*args, **kwargs)
        self._iterable_class = EavModelIterable

    @eav_filter
    def filter(self, *args: Any, **kwargs: Any) -> EavQuerySet[_ModelT]:
        """Filter after passing the arguments through :func:`eav_filter`.

        The result is passed to the ``Manager`` filter method.
        """
        return super().filter(*args, **kwargs)

    @eav_filter
    def exclude(self, *args: Any, **kwargs: Any) -> EavQuerySet[_ModelT]:
        """Exclude after passing the arguments through :func:`eav_filter`.

        The result is passed to the ``Manager`` exclude method.
        """
        return super().exclude(*args, **kwargs)

    @eav_filter
    def get(self, *args: Any, **kwargs: Any) -> _ModelT:
        """Get after passing the arguments through :func:`eav_filter`.

        The result is passed to the ``Manager`` get method.
        """
        return super().get(*args, **kwargs)

    def bulk_create(  # noqa: PLR0913, PLR0917
        self,
        objs: Iterable[_ModelT],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,  # noqa: FBT001, FBT002
        update_conflicts: bool = False,  # noqa: FBT001, FBT002
        update_fields: Collection[str] | None = None,
        unique_fields: Collection[str] | None = None,
    ) -> list[_ModelT]:
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

        if writer is None:
            return super().bulk_create(
                objs,
                batch_size=batch_size,
                ignore_conflicts=ignore_conflicts,
                update_conflicts=update_conflicts,
                update_fields=update_fields,
                unique_fields=unique_fields,
            )

        if ignore_conflicts or update_conflicts:
            raise NotSupportedError(
                "bulk_create() cannot store EAV values together with conflict handling",
            )

        created: list[_ModelT] = []
        with transaction.atomic(using=self.db):
            writer.validate_new(objs)

            for chunk in chunked(objs, writer.chunk_size):
                chunk_created = super().bulk_create(chunk, batch_size=batch_size)
                writer.write(chunk_created)
                created.extend(chunk_created)

        return created

    def bulk_update(
        self,
        objs: Iterable[_ModelT],
        fields: Iterable[str],
        batch_size: int | None = None,
    ) -> int:
        """
        Update *objs*, including EAV attributes named like ``eav__<slug>``.

        EAV attributes are written from the values assigned on each instance
        (``obj.eav.color = "red"``); instances without an assigned value for a
        listed attribute are left alone, and a value of ``None`` deletes it.
        Like Django's ``bulk_update`` this sends no signals.
        """
        objs = list(objs)
        field_names = list(fields)
        eav_slugs, model_fields = split_eav_fields(
            config_of(self.model).eav_attr,
            field_names,
        )

        if not eav_slugs:
            return super().bulk_update(objs, field_names, batch_size)

        if any(candidate.pk is None for candidate in objs):
            raise ValueError("All bulk_update() objects must have a primary key set.")

        writer = BulkValueWriter(self.model, batch_size)

        with transaction.atomic(using=self.db):
            updated = 0
            if model_fields:
                updated = super().bulk_update(objs, model_fields, batch_size)
            writer.validate_assigned(objs, eav_slugs)

            for chunk in chunked(objs, writer.chunk_size):
                writer.write(chunk, eav_slugs)

        return updated

    def order_by(self, *fields: Any) -> Self:
        """Order by EAV attributes and regular fields.

        EAV attributes are named ``eav__<slug>``, optionally prefixed with ``-``.

        Each EAV attribute is annotated with a correlated subquery that reads
        the entity's value, so this works for integer and UUID primary keys,
        for empty querysets, and for any value type the database can sort.
        """
        eav_attr = config_of(self.model).eav_attr
        queryset: QuerySet[_ModelT] = self
        ordering: list[Any] = []

        for field in fields:
            slug = eav_order_slug(field, eav_attr)

            if slug is None:
                ordering.append(field)
                continue

            alias = f"_eav_order_{slug}"
            if alias not in queryset.query.annotations:
                queryset = queryset.annotate(
                    **{alias: order_subquery(self.model, slug)},
                )
            ordering.append(f"-{alias}" if field.startswith("-") else alias)

        return cast("Self", QuerySet.order_by(queryset, *ordering))
