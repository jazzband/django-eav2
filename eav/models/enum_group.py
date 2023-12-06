from typing import TYPE_CHECKING, Any, Tuple

from django.db import models
from django.db.models import ManyToManyField
from django.utils.translation import gettext_lazy as _

from eav.logic.managers import EnumGroupManager
from eav.logic.object_pk import get_pk_format
from eav.settings import CHARFIELD_LENGTH

if TYPE_CHECKING:
    from .enum_value import EnumValue


class EnumGroup(models.Model):
    """
    *EnumGroup* objects have two fields - a *name* ``CharField`` and *values*,
    a ``ManyToManyField`` to :class:`EnumValue`. :class:`Attribute` classes
    with datatype *TYPE_ENUM* have a ``ForeignKey`` field to *EnumGroup*.

    See :class:`EnumValue` for an example.
    """

    objects = EnumGroupManager()

    class Meta:
        verbose_name = _('EnumGroup')
        verbose_name_plural = _('EnumGroups')

    id = get_pk_format()

    name = models.CharField(
        unique=True,
        max_length=CHARFIELD_LENGTH,
        verbose_name=_('Name'),
    )
    values: "ManyToManyField[EnumValue, Any]" = ManyToManyField(
        "eav.EnumValue",
        verbose_name=_('Enum group'),
    )

    def __str__(self) -> str:
        """String representation of `EnumGroup` instance."""
        return str(self.name)

    def __repr__(self) -> str:
        """String representation of `EnumGroup` object."""
        return f'<EnumGroup {self.name}>'

    def natural_key(self) -> Tuple[str]:
        """
        Retrieve the natural key for the EnumGroup instance.

        The natural key for an EnumGroup is defined by its `name`. This method
        returns the name of the instance as a single-element tuple.

        Returns
        -------
            tuple: A tuple containing the name of the EnumGroup instance.
        """
        return (self.name,)
