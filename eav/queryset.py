"""A queryset for models that are registered with eav.

:class:`EavQuerySet` understands ``eav__<slug>`` in ``filter()`` and
``exclude()``, and in ``order_by()``, and writes EAV values in bulk. How a
filter on an attribute becomes SQL is explained in ``eav.logic.filtering``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from django.db import models, transaction
from django.db.models.query import ModelIterable, QuerySet
from django.db.utils import NotSupportedError

from eav.logic.bulk import BulkValueWriter, chunked, split_eav_fields
from eav.logic.entities import config_of
from eav.logic.filtering import expand_filters
from eav.logic.ordering import eav_order_slug, order_subquery
from eav.logic.schema import shared_schema_for

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator

    from typing_extensions import Self

_ModelT = TypeVar("_ModelT", bound=models.Model)


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

    def filter(self, *args: Any, **kwargs: Any) -> EavQuerySet[_ModelT]:
        """Filter by ordinary fields and by ``eav__<slug>`` attributes."""
        return super().filter(expand_filters(self.model, args, kwargs))

    def exclude(self, *args: Any, **kwargs: Any) -> EavQuerySet[_ModelT]:
        """Exclude by ordinary fields and by ``eav__<slug>`` attributes."""
        return super().exclude(expand_filters(self.model, args, kwargs))

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
