# ruff: noqa: UP007

from typing import TYPE_CHECKING, Optional, Tuple

from django.contrib.contenttypes import fields as generic
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import ForeignKey
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from eav.fields import CSVField
from eav.logic.managers import ValueManager
from eav.logic.object_pk import get_pk_format

if TYPE_CHECKING:
    from .attribute import Attribute
    from .enum_value import EnumValue


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

    objects = ValueManager()

    class Meta:
        verbose_name = _('Value')
        verbose_name_plural = _('Values')

    id = get_pk_format()

    # Direct foreign keys
    attribute: "ForeignKey[Attribute]" = ForeignKey(
        "eav.Attribute",
        db_index=True,
        on_delete=models.PROTECT,
        verbose_name=_('Attribute'),
    )

    # Entity generic relationships. Rather than rely on database casting,
    # this will instead use a separate ForeignKey field attribute that matches
    # the FK type of the entity.
    entity_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('Entity id'),
    )

    entity_uuid = models.UUIDField(
        blank=True,
        null=True,
        verbose_name=_('Entity uuid'),
    )

    entity_ct = ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name='value_entities',
        verbose_name=_('Entity ct'),
    )

    entity_pk_int = generic.GenericForeignKey(
        ct_field='entity_ct',
        fk_field='entity_id',
    )

    entity_pk_uuid = generic.GenericForeignKey(
        ct_field='entity_ct',
        fk_field='entity_uuid',
    )

    # Model attributes
    created = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Created'),
    )

    modified = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified'),
    )

    # Value attributes
    value_bool = models.BooleanField(
        blank=True,
        null=True,
        verbose_name=_('Value bool'),
    )
    value_csv = CSVField(
        blank=True,
        null=True,
        verbose_name=_('Value CSV'),
    )
    value_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Value date'),
    )
    value_float = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_('Value float'),
    )
    value_int = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Value int'),
    )
    value_text = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Value text'),
    )

    value_json = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        verbose_name=_('Value JSON'),
    )

    value_enum: "ForeignKey[Optional[EnumValue]]" = ForeignKey(
        "eav.EnumValue",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='eav_values',
        verbose_name=_('Value enum'),
    )

    # Value object relationship
    generic_value_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('Generic value id'),
    )

    generic_value_ct = ForeignKey(
        ContentType,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='value_values',
        verbose_name=_('Generic value content type'),
    )

    value_object = generic.GenericForeignKey(
        ct_field='generic_value_ct',
        fk_field='generic_value_id',
    )

    def natural_key(self) -> Tuple[Tuple[str, str], int, str]:
        """
        Retrieve the natural key for the Value instance.

        The natural key for a Value is a combination of its `attribute` natural key,
        `entity_id`, and `entity_uuid`. This method returns a tuple containing these
        three elements.

        Returns
        -------
            tuple: A tuple containing the natural key of the attribute, entity ID,
                and entity UUID of the Value instance.
        """
        return (self.attribute.natural_key(), self.entity_id, self.entity_uuid)

    def __str__(self) -> str:
        """String representation of a Value."""
        entity = self.entity_pk_uuid if self.entity_uuid else self.entity_pk_int
        return f'{self.attribute.name}: "{self.value}" ({entity})'

    def __repr__(self) -> str:
        """Representation of Value object."""
        entity = self.entity_pk_uuid if self.entity_uuid else self.entity_pk_int
        return f'{self.attribute.name}: "{self.value}" ({entity})'

    def save(self, *args, **kwargs):
        """Validate and save this value."""
        self.full_clean()
        super().save(*args, **kwargs)

    def _get_value(self):
        """Return the python object this value is holding."""
        return getattr(self, f'value_{self.attribute.datatype}')

    def _set_value(self, new_value):
        """Set the object this value is holding."""
        setattr(self, f'value_{self.attribute.datatype}', new_value)

    value = property(_get_value, _set_value)
