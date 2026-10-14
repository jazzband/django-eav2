"""Write the EAV values of many entities in a few queries per batch of rows."""

from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, cast

from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.db.utils import NotSupportedError

from eav.logic.entity_pk import get_entity_pk_type
from eav.logic.schema import SharedSchema
from eav.models import Attribute, EnumValue, Value

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

    from django.db.models import Field, Model

_NO_PRIMARY_KEYS: Final = "Primary keys are needed to store EAV values; use UUID keys."

#: The :class:`Value` columns that hold each datatype.
_VALUE_COLUMNS: Final = MappingProxyType(
    {
        Attribute.TYPE_TEXT: ("value_text",),
        Attribute.TYPE_FLOAT: ("value_float",),
        Attribute.TYPE_INT: ("value_int",),
        Attribute.TYPE_DATE: ("value_date",),
        Attribute.TYPE_BOOLEAN: ("value_bool",),
        Attribute.TYPE_OBJECT: ("generic_value_ct", "generic_value_id"),
        Attribute.TYPE_ENUM: ("value_enum",),
        Attribute.TYPE_JSON: ("value_json",),
        Attribute.TYPE_CSV: ("value_csv",),
    },
)


def chunked(sequence: Sequence[Any], size: int) -> Iterator[Sequence[Any]]:
    """Yield *sequence* in slices of at most *size*."""
    for start in range(0, len(sequence), size):
        yield sequence[start : start + size]


def entity_of(instance: Model) -> Any:
    """The EAV helper attached to *instance*."""
    config_cls = getattr(type(instance), "_eav_config_cls")  # noqa: B009
    return getattr(instance, config_cls.eav_attr)


def assigned_pairs(
    instance: Model,
    attributes: Mapping[str, Attribute],
    slugs: Sequence[str] | None,
) -> Iterator[tuple[Attribute, object]]:
    """Yield the ``(attribute, raw value)`` pairs assigned on *instance*."""
    assigned = entity_of(instance).assigned_values()

    for slug, attribute in attributes.items():
        if slug in assigned and (slugs is None or slug in slugs):
            yield attribute, assigned[slug]


class ValueBuilder:
    """Builds unsaved :class:`Value` objects for the instances of one model."""

    def __init__(self, model_cls: type[Model]) -> None:
        """Prepare to build values for instances of *model_cls*."""
        self.pk_field = get_entity_pk_type(model_cls)
        self._content_type = ContentType.objects.get_for_model(model_cls)

    def build(
        self,
        instance: Model,
        attribute: Attribute,
        raw_value: object,
    ) -> Value:
        """Build the value of *attribute* for *instance*, cleaned and typed."""
        eav_value = Value(
            entity_ct_id=self._content_type.pk,
            attribute_id=attribute.pk,
            **{self.pk_field: instance.pk},
        )

        if attribute.datatype == Attribute.TYPE_OBJECT:
            eav_value.value_object = raw_value
        elif attribute.datatype == Attribute.TYPE_ENUM:
            eav_value.value_enum = (
                raw_value
                if isinstance(raw_value, EnumValue)
                else attribute.enum_choices[str(raw_value)]
            )
        else:
            column = _VALUE_COLUMNS[attribute.datatype][0]
            field = cast("Field[Any, Any]", Value._meta.get_field(column))  # noqa: SLF001
            setattr(eav_value, column, field.clean(raw_value, eav_value))

        return eav_value

    def delete(self, attribute: Attribute, pks: Sequence[Any], size: int) -> None:
        """Delete the values of *attribute* for the entities with these *pks*."""
        for chunk in chunked(pks, size):
            Value.objects.filter(
                entity_ct=self._content_type,
                attribute=attribute,
                **{f"{self.pk_field}__in": chunk},
            ).delete()

    def upsert(self, datatype: str, rows: list[Value], size: int) -> None:
        """Insert *rows* of one datatype, updating any that already exist."""
        features = connections[Value.objects.db].features
        # MySQL and MariaDB update on any unique key and reject naming the fields.
        unique_fields = (
            ["entity_ct", "attribute", self.pk_field]
            if features.supports_update_conflicts_with_target
            else None
        )

        Value.objects.bulk_create(
            rows,
            batch_size=size,
            update_conflicts=True,
            unique_fields=unique_fields,
            update_fields=[*_VALUE_COLUMNS[datatype], "modified"],
        )


class WritePlan:
    """The values to upsert and the attributes to clear, for a set of instances."""

    def __init__(self) -> None:
        """Start with nothing to write."""
        self.upserts: dict[str, list[Value]] = defaultdict(list)
        self.deletes: dict[Attribute, list[Any]] = defaultdict(list)

    def collect(
        self,
        instance: Model,
        pairs: Iterable[tuple[Attribute, object]],
        builder: ValueBuilder,
    ) -> None:
        """Add what the assigned *pairs* of *instance* require."""
        for attribute, raw_value in pairs:
            if raw_value is None or raw_value == "":
                self.deletes[attribute].append(instance.pk)
            else:
                built = builder.build(instance, attribute, raw_value)
                self.upserts[attribute.datatype].append(built)

    def flush(self, builder: ValueBuilder, size: int) -> None:
        """Run the deletes, then the upserts, in batches of *size*."""
        for attribute, pks in self.deletes.items():
            builder.delete(attribute, pks, size)

        for datatype, rows in self.upserts.items():
            builder.upsert(datatype, rows, size)


class BulkValueWriter:
    """
    Validates and writes the EAV values assigned to many instances of a model.

    Attributes are loaded once for the whole batch. Values are written with one
    upsert per datatype per chunk and one delete per attribute that is being
    cleared. Queries grow with the number of rows divided by the batch size
    (about one per 1000 rows), not with the number of entities.

    Django's bulk operations send no signals, and neither does this.
    """

    def __init__(self, model_cls: type[Model], chunk_size: int | None = None) -> None:
        """Prepare to write values for instances of *model_cls*."""
        config_cls = getattr(model_cls, "_eav_config_cls")  # noqa: B009
        self.chunk_size = chunk_size or config_cls.bulk_batch_size
        self._schema = SharedSchema(model_cls)
        self._builder = ValueBuilder(model_cls)

    @classmethod
    def for_objects(
        cls,
        model_cls: type[Model],
        instances: Iterable[Model],
        chunk_size: int | None = None,
    ) -> BulkValueWriter | None:
        """Return a writer, or ``None`` when no instance has assigned values."""
        config_cls = getattr(model_cls, "_eav_config_cls", None)

        if config_cls is None or config_cls.manager_only:
            return None

        if not any(entity_of(candidate).assigned_values() for candidate in instances):
            return None

        return cls(model_cls, chunk_size)

    def validate_new(self, instances: Iterable[Model]) -> None:
        """
        Check every new instance as saving it would, before anything is written.

        Raises ``ValidationError`` or ``IllegalAssignmentException`` as
        :meth:`eav.models.Entity.validate_attributes` does.
        """
        for instance in instances:
            entity = entity_of(instance)
            entity.use_schema(self._schema)
            entity.validate_attributes()

    def validate_assigned(self, instances: Iterable[Model], slugs: list[str]) -> None:
        """Check the values assigned to the attributes in *slugs*."""
        attributes = self._schema.load()

        for slug in slugs:
            if slug not in attributes:
                raise Attribute.DoesNotExist(slug)

        for instance in instances:
            for attribute, raw_value in assigned_pairs(instance, attributes, slugs):
                attribute.validate_assignment(raw_value)

    def write(
        self,
        instances: Sequence[Model],
        slugs: list[str] | None = None,
    ) -> None:
        """
        Store the assigned values of *instances*, which must have primary keys.

        Only the attributes in *slugs* are written when it is given. Values set
        to ``None`` or an empty string are deleted.
        """
        if any(instance.pk is None for instance in instances):
            raise NotSupportedError(_NO_PRIMARY_KEYS)

        plan = WritePlan()
        attributes = self._schema.load()

        for instance in instances:
            pairs = assigned_pairs(instance, attributes, slugs)
            plan.collect(instance, pairs, self._builder)

        plan.flush(self._builder, self.chunk_size)

        for instance in instances:
            entity_of(instance).clear_cache()
