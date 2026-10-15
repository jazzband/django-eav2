"""Helpers for rewriting lookups on EAV attributes into lookups on values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eav.models import Attribute, EnumValue

if TYPE_CHECKING:
    from django.db.models import QuerySet


def value_lookup(datatype: str, candidate: object, extra: str | None) -> str:
    """
    Return the name of the :class:`Value` lookup to filter an attribute with.

    Args:
        datatype: The datatype of the attribute.
        candidate: What the attribute is compared with.
        extra: A trailing lookup such as ``startswith``, or ``None``.
    """
    suffix = f"__{extra}" if extra else ""

    if datatype == Attribute.TYPE_ENUM and not isinstance(candidate, EnumValue):
        return f"value_{datatype}__value{suffix}"

    if datatype == Attribute.TYPE_OBJECT:
        return "generic_value_id"

    return f"value_{datatype}{suffix}"


def leaf_queryset(
    model_cls: Any,
    leaf: tuple[str, Any],
    in_name: str,
) -> QuerySet[Any]:
    """
    Return the entities matched by a ``<in_name>`` or ``pk__in`` leaf.

    A leaf is either an ``eav_values__in`` lookup, which is turned into a
    ``pk__in`` one, or already a ``pk__in`` lookup whose operand is a queryset.
    Entities are returned as a queryset so that set operators can be applied.
    """
    lookup, operand = leaf

    if lookup == in_name or hasattr(operand, "__contains__"):
        return model_cls.objects.filter(**{in_name: operand})  # type: ignore[no-any-return]

    return operand  # type: ignore[no-any-return]
