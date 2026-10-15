"""Rewrite filters on EAV attributes into queries that the database can run.

A user writes ``Patient.objects.filter(eav__age__gt=30)``. An attribute value is a
row of the values table, not a column of the patient, so that condition really
asks: "does this patient have a stored value for ``age`` that is over 30?"

Each condition on an attribute becomes its own ``EXISTS`` subquery, one that
looks for such a row for the patient it is checking. Do not replace this with a
join on the values table. Every condition of one ``filter()`` call shares a
single join, so ``eav__a=1`` together with ``eav__b=2`` asks for one row that
belongs to two attributes at once, which matches nothing, and ``~Q(eav__a=1)``
negates a single value row instead of the whole patient. With ``EXISTS``, every
condition is an independent yes-or-no fact about the patient, so ``&``, ``|``,
``~``, and ``exclude()`` behave as they do for ordinary fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.db import models

from eav.logic.entities import config_of
from eav.logic.entity_pk import get_entity_pk_type
from eav.logic.ordering import get_attribute
from eav.models import Attribute, EnumValue, Value

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

# A lookup on an attribute has at least a prefix and a slug: ``eav__age``.
_EAV_LOOKUP_MIN_PARTS: Final = 2
_ISNULL_NOT_BOOLEAN: Final = (
    "The value of an isnull lookup on an EAV attribute must be True or False."
)


def expand_filters(
    model_cls: type[models.Model],
    filter_args: Iterable[Any],
    filter_kwargs: Mapping[str, Any],
) -> models.Q:
    """Return the arguments of ``filter()`` as one ``Q`` that the database can run.

    Django treats ``filter(*filter_args, **filter_kwargs)`` as one ``Q`` that
    combines all of them with AND, and ``exclude()`` as the negation of that
    ``Q``. This returns that ``Q`` with every condition on an EAV attribute
    replaced by an ``EXISTS`` subquery. Nothing passed in is changed.
    """
    return _expand_condition(
        models.Q(*filter_args, **filter_kwargs),
        model_cls,
    )


def _expand_condition(
    condition: models.Q,
    model_cls: type[models.Model],
) -> models.Q:
    """Return a copy of *condition* with its EAV lookups replaced."""
    expanded_children: list[Any] = []

    for child in condition.children:
        if isinstance(child, models.Q):
            expanded_children.append(_expand_condition(child, model_cls))
        elif isinstance(child, tuple):
            lookup, lookup_value = child
            expanded_children.append(_expand_lookup(model_cls, lookup, lookup_value))
        else:
            # An expression such as ``Exists(...)`` has nothing to expand.
            expanded_children.append(child)

    return models.Q(
        *expanded_children,
        _connector=condition.connector,
        _negated=condition.negated,
    )


def _expand_lookup(
    model_cls: type[models.Model],
    lookup: str,
    lookup_value: Any,
) -> models.Q:
    """Return the condition for one lookup, such as ``eav__age__gt`` with ``30``.

    A lookup that is not on an EAV attribute is returned as it is.
    """
    lookup_parts = lookup.split("__")
    eav_attr = config_of(model_cls).eav_attr

    if len(lookup_parts) < _EAV_LOOKUP_MIN_PARTS or lookup_parts[0] != eav_attr:
        return models.Q(**{lookup: lookup_value})

    slug, *trailing_lookups = lookup_parts[1:]
    datatype = get_attribute(slug).datatype

    if trailing_lookups == ["isnull"]:
        return _entity_has_no_value(model_cls, slug, lookup_value)

    value_lookup = _value_lookup(datatype, lookup_value, trailing_lookups)
    matching_values = Value.objects.filter(
        **{value_lookup: lookup_value, "attribute__slug": slug},
    )
    return _entity_has_value(model_cls, matching_values)


def _entity_has_no_value(
    model_cls: type[models.Model],
    slug: str,
    is_missing: Any,
) -> models.Q:
    """Return the condition for ``eav__<slug>__isnull``.

    An entity without a value for the attribute has no row to compare, so
    "is null" means "has no row for this attribute at all". Saving ``None`` or an
    empty string deletes the row, which makes a row and a value the same thing.
    """
    if not isinstance(is_missing, bool):
        raise ValueError(_ISNULL_NOT_BOOLEAN)  # noqa: TRY004

    has_value = _entity_has_value(
        model_cls,
        Value.objects.filter(attribute__slug=slug),
    )
    return ~has_value if is_missing else has_value


def _entity_has_value(
    model_cls: type[models.Model],
    matching_values: models.QuerySet[Value],
) -> models.Q:
    """Return the condition that the entity has one of *matching_values*.

    It is an ``EXISTS`` subquery that looks, for the entity row it is checking,
    for a matching value of that entity.
    """
    entity_values = matching_values.filter(
        entity_ct=ContentType.objects.get_for_model(model_cls),
        **{get_entity_pk_type(model_cls): models.OuterRef("pk")},
    )
    return models.Q(models.Exists(entity_values))


def _value_lookup(
    datatype: str,
    lookup_value: object,
    trailing_lookups: list[str],
) -> str:
    """Return the :class:`Value` lookup that compares an attribute of *datatype*.

    Args:
        datatype: The datatype of the attribute.
        lookup_value: What the attribute is compared with.
        trailing_lookups: The lookups after the slug, such as ``["startswith"]``
            or ``["year", "gt"]``. It is empty for a plain comparison.
    """
    suffix = "".join(f"__{name}" for name in trailing_lookups)

    if datatype == Attribute.TYPE_ENUM and not isinstance(lookup_value, EnumValue):
        return f"value_{datatype}__value{suffix}"

    if datatype == Attribute.TYPE_OBJECT:
        if trailing_lookups:
            extra = "__".join(trailing_lookups)
            message = f"Object attributes support only equality, not {extra!r}."
            raise FieldError(message)

        return "generic_value_id"

    return f"value_{datatype}{suffix}"
