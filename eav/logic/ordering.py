"""Helpers used by :class:`~eav.queryset.EavQuerySet` to order by EAV attributes."""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model, OuterRef, Subquery
from django.db.utils import NotSupportedError

from eav.logic.entity_pk import get_entity_pk_type
from eav.models import Attribute, Value


def eav_order_slug(field: object, eav_attr: str) -> str | None:
    """
    Return the attribute slug when *field* orders by an EAV attribute.

    Returns ``None`` for any other ordering term, and raises for nested terms
    such as ``eav__a__b``, which are not supported.
    """
    if not isinstance(field, str):
        return None

    term = field.removeprefix("-").split("__")

    if term[0] != eav_attr or len(term) == 1:
        return None

    if len(term) > 2:  # noqa: PLR2004
        raise NotSupportedError(
            "EAV does not support ordering through foreign-key chains",
        )

    return term[1]


def order_subquery(model_cls: type[Model], slug: str) -> Subquery:
    """Build a subquery selecting an entity's value for the attribute *slug*."""
    try:
        attribute = Attribute.objects.get(slug=slug)
    except ObjectDoesNotExist as err:
        raise ObjectDoesNotExist(f'Cannot find EAV attribute "{slug}"') from err

    if attribute.datatype == Attribute.TYPE_OBJECT:
        raise NotSupportedError("EAV does not support ordering by object attributes")

    entity_values = Value.objects.filter(
        attribute=attribute,
        entity_ct=ContentType.objects.get_for_model(model_cls),
        **{get_entity_pk_type(model_cls): OuterRef("pk")},
    )
    return Subquery(entity_values.values(f"value_{attribute.datatype}")[:1])
