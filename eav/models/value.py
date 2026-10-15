from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.contrib.contenttypes import fields as generic
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from eav.fields import CSVField
from eav.logic.dates import as_datetime
from eav.logic.managers import ValueManager
from eav.logic.object_pk import get_pk_format

if TYPE_CHECKING:
    from uuid import UUID

    from eav.models.attribute import Attribute
    from eav.models.enum_value import EnumValue


_NaturalKey = tuple[tuple[str, str], int | None, "UUID | None"]

#: Related fields whose existence checks cost a query each.
_RELATION_FIELDS = frozenset(
    ("attribute", "entity_ct", "value_enum", "generic_value_ct"),
)


class Value(models.Model):
    """
    Putting the **V** in *EAV*.

    This model stores the value for one particular :class:`Attribute` for
    some entity.

    As with most EAV implementations, most of the columns of this model will
    be blank, as onle one *value_* field will be used.

    Example::

        import eav
        from django.contrib.auth.models import User

        eav.register(User)

        u = User.objects.create(username='crazy_dev_user')
        a = Attribute.objects.create(name='Fav Drink', datatype='text')

        Value.objects.create(entity = u, attribute = a, value_text = 'red bull')
        # = <Value: crazy_dev_user - Fav Drink: "red bull">
    """

    id = get_pk_format()

    # Direct foreign keys
    attribute: models.ForeignKey[Attribute] = models.ForeignKey(
        "eav.Attribute",
        db_index=True,
        on_delete=models.PROTECT,
        verbose_name=_("Attribute"),
    )

    # Entity generic relationships. Rather than rely on database casting,
    # this will instead use a separate ForeignKey field attribute that matches
    # the FK type of the entity.
    entity_id = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Entity id"),
    )

    entity_uuid = models.UUIDField(
        blank=True,
        null=True,
        verbose_name=_("Entity uuid"),
    )

    entity_ct = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name="value_entities",
        verbose_name=_("Entity ct"),
    )

    entity_pk_int = generic.GenericForeignKey(
        ct_field="entity_ct",
        fk_field="entity_id",
    )

    entity_pk_uuid = generic.GenericForeignKey(
        ct_field="entity_ct",
        fk_field="entity_uuid",
    )

    # Model attributes
    created = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Created"),
    )

    modified = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Modified"),
    )

    # Value attributes
    value_bool = models.BooleanField(
        blank=True,
        null=True,
        verbose_name=_("Value bool"),
    )
    value_csv = CSVField(
        blank=True,
        null=True,
        verbose_name=_("Value CSV"),
    )
    value_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Value date"),
    )
    value_float = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Value float"),
    )
    value_int = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Value int"),
    )
    value_text = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Value text"),
    )

    value_json = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        verbose_name=_("Value JSON"),
    )

    value_enum: models.ForeignKey[EnumValue | None] = models.ForeignKey(
        "eav.EnumValue",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="eav_values",
        verbose_name=_("Value enum"),
    )

    # Value object relationship
    generic_value_id = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Generic value id"),
    )

    generic_value_ct = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="value_values",
        verbose_name=_("Generic value content type"),
    )

    value_object = generic.GenericForeignKey(
        ct_field="generic_value_ct",
        fk_field="generic_value_id",
    )

    objects = ValueManager()

    class Meta:
        verbose_name = _("Value")
        verbose_name_plural = _("Values")

        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["attribute", "value_int"],
                name="eav_value_attr_int_idx",
            ),
            models.Index(
                fields=["attribute", "value_float"],
                name="eav_value_attr_float_idx",
            ),
            models.Index(
                fields=["attribute", "value_date"],
                name="eav_value_attr_date_idx",
            ),
            models.Index(
                fields=["attribute", "value_enum"],
                name="eav_value_attr_enum_idx",
            ),
        ]

        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["entity_ct", "attribute", "entity_uuid"],
                name="unique_entity_uuid_per_attribute",
            ),
            models.UniqueConstraint(
                fields=["entity_ct", "attribute", "entity_id"],
                name="unique_entity_id_per_attribute",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(entity_id__isnull=False, entity_uuid__isnull=True)
                    | models.Q(entity_id__isnull=True, entity_uuid__isnull=False)
                ),
                name="ensure_entity_id_xor_entity_uuid",
            ),
        ]

    def __str__(self) -> str:
        """Return the string representation of a Value."""
        entity = self.entity_pk_uuid if self.entity_uuid else self.entity_pk_int
        name = self.attribute.name
        return f'{name}: "{self.value}" ({entity})'

    __repr__ = __str__

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Validate and save this value."""
        self.full_clean()
        super().save(*args, **kwargs)

    def save_checked(self, *args: Any, **kwargs: Any) -> None:
        """
        Clean this value's own fields, then save.

        Unlike :meth:`save` this skips the checks that query the database
        (that related objects exist, that the unique constraints hold). It is
        used by ``Entity.save``, which has already validated the value and
        loaded the existing rows; the database still enforces the constraints.
        """
        self.clean_own_fields()
        models.Model.save(self, *args, **kwargs)

    def clean_own_fields(self) -> None:
        """
        Clean the fields that hold this value, converting them to Python types.

        Related fields are skipped, as checking they exist costs a query each.
        """
        self.clean_fields(exclude=_RELATION_FIELDS)

    def natural_key(self) -> _NaturalKey:
        """
        Retrieve the natural key for the Value instance.

        The natural key for a Value is a combination of its `attribute` natural key,
        `entity_id`, and `entity_uuid`. This method returns a tuple containing these
        three elements.

        Returns:
            tuple: A tuple containing the natural key of the attribute, entity ID,
                and entity UUID of the Value instance.
        """
        attribute_key = self.attribute.natural_key()
        return (attribute_key, self.entity_id, self.entity_uuid)

    def _get_value(self) -> Any:
        """Return the python object this value is holding."""
        datatype = self.attribute.datatype
        return getattr(self, f"value_{datatype}")

    def _set_value(self, new_value: Any) -> None:
        """Set the object this value is holding."""
        datatype = self.attribute.datatype

        if datatype == "date":
            new_value = as_datetime(new_value)

        setattr(self, f"value_{datatype}", new_value)

    value = property(_get_value, _set_value)
