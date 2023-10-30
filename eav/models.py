"""
This module defines the four concrete, non-abstract models:
    * :class:`Value`
    * :class:`Attribute`
    * :class:`EnumValue`
    * :class:`EnumGroup`

Along with the :class:`Entity` helper class and :class:`EAVModelMeta`
optional metaclass for each eav model class.
"""

from copy import copy
from typing import Tuple

from django.contrib.contenttypes import fields as generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from eav import register
from eav.exceptions import IllegalAssignmentException
from eav.fields import CSVField, EavDatatypeField
from eav.logic.entity_pk import get_entity_pk_type
from eav.logic.managers import (
    AttributeManager,
    EnumGroupManager,
    EnumValueManager,
    ValueManager,
)
from eav.logic.object_pk import get_pk_format
from eav.logic.slug import SLUGFIELD_MAX_LENGTH, generate_slug
from eav.validators import (
    validate_bool,
    validate_csv,
    validate_date,
    validate_enum,
    validate_float,
    validate_int,
    validate_json,
    validate_object,
    validate_text,
)

try:
    from typing import Final
except ImportError:
    from typing_extensions import Final


CHARFIELD_LENGTH: Final = 100


class EnumValue(models.Model):
    """
    *EnumValue* objects are the value 'choices' to multiple choice *TYPE_ENUM*
    :class:`Attribute` objects. They have only one field, *value*, a
    ``CharField`` that must be unique.

    For example::

        yes = EnumValue.objects.create(value='Yes') # doctest: SKIP
        no = EnumValue.objects.create(value='No')
        unknown = EnumValue.objects.create(value='Unknown')

        ynu = EnumGroup.objects.create(name='Yes / No / Unknown')
        ynu.values.add(yes, no, unknown)

        Attribute.objects.create(name='has fever?',
            datatype=Attribute.TYPE_ENUM, enum_group=ynu)
        # = <Attribute: has fever? (Multiple Choice)>

    .. note::
       The same *EnumValue* objects should be reused within multiple
       *EnumGroups*.  For example, if you have one *EnumGroup* called: *Yes /
       No / Unknown* and another called *Yes / No / Not applicable*, you should
       only have a total of four *EnumValues* objects, as you should have used
       the same *Yes* and *No* *EnumValues* for both *EnumGroups*.
    """

    objects = EnumValueManager()

    class Meta:
        verbose_name = _('EnumValue')
        verbose_name_plural = _('EnumValues')

    id = get_pk_format()

    value = models.CharField(
        _('Value'),
        db_index=True,
        unique=True,
        max_length=SLUGFIELD_MAX_LENGTH,
    )

    def natural_key(self) -> Tuple[str]:
        """
        Retrieve the natural key for the EnumValue instance.

        The natural key for an EnumValue is defined by its `value`. This method returns
        the value of the instance as a single-element tuple.

        Returns:
            tuple: A tuple containing the value of the EnumValue instance.
        """
        return (self.value,)

    def __str__(self):
        """String representation of `EnumValue` instance."""
        return str(
            self.value,
        )

    def __repr__(self):
        """String representation of `EnumValue` object."""
        return '<EnumValue {0}>'.format(self.value)


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
    values = models.ManyToManyField(
        EnumValue,
        verbose_name=_('Enum group'),
    )

    def natural_key(self) -> Tuple[str]:
        """
        Retrieve the natural key for the EnumGroup instance.

        The natural key for an EnumGroup is defined by its `name`. This method
        returns the name of the instance as a single-element tuple.

        Returns:
            tuple: A tuple containing the name of the EnumGroup instance.
        """
        return (self.name,)

    def __str__(self):
        """String representation of `EnumGroup` instance."""
        return str(self.name)

    def __repr__(self):
        """String representation of `EnumGroup` object."""
        return '<EnumGroup {0}>'.format(self.name)


class Attribute(models.Model):
    """
    Putting the **A** in *EAV*. This holds the attributes, or concepts.
    Examples of possible *Attributes*: color, height, weight, number of
    children, number of patients, has fever?, etc...

    Each attribute has a name, and a description, along with a slug that must
    be unique.  If you don't provide a slug, a default slug (derived from
    name), will be created.

    The *required* field is a boolean that indicates whether this EAV attribute
    is required for entities to which it applies. It defaults to *False*.

    .. warning::
       Just like a normal model field that is required, you will not be able
       to save or create any entity object for which this attribute applies,
       without first setting this EAV attribute.

    There are 7 possible values for datatype:

        * int (TYPE_INT)
        * float (TYPE_FLOAT)
        * text (TYPE_TEXT)
        * date (TYPE_DATE)
        * bool (TYPE_BOOLEAN)
        * object (TYPE_OBJECT)
        * enum (TYPE_ENUM)
        * json (TYPE_JSON)
        * csv (TYPE_CSV)


    Examples::

        Attribute.objects.create(name='Height', datatype=Attribute.TYPE_INT)
        # = <Attribute: Height (Integer)>

        Attribute.objects.create(name='Color', datatype=Attribute.TYPE_TEXT)
        # = <Attribute: Color (Text)>

        yes = EnumValue.objects.create(value='yes')
        no = EnumValue.objects.create(value='no')
        unknown = EnumValue.objects.create(value='unknown')
        ynu = EnumGroup.objects.create(name='Yes / No / Unknown')
        ynu.values.add(yes, no, unknown)

        Attribute.objects.create(name='has fever?', datatype=Attribute.TYPE_ENUM, enum_group=ynu)
        # = <Attribute: has fever? (Multiple Choice)>

    .. warning:: Once an Attribute has been used by an entity, you can not
                 change it's datatype.
    """

    objects = AttributeManager()

    class Meta:
        ordering = ['name']
        verbose_name = _('Attribute')
        verbose_name_plural = _('Attributes')

    TYPE_TEXT = 'text'
    TYPE_FLOAT = 'float'
    TYPE_INT = 'int'
    TYPE_DATE = 'date'
    TYPE_BOOLEAN = 'bool'
    TYPE_OBJECT = 'object'
    TYPE_ENUM = 'enum'
    TYPE_JSON = 'json'
    TYPE_CSV = 'csv'

    DATATYPE_CHOICES = (
        (TYPE_TEXT, _('Text')),
        (TYPE_DATE, _('Date')),
        (TYPE_FLOAT, _('Float')),
        (TYPE_INT, _('Integer')),
        (TYPE_BOOLEAN, _('True / False')),
        (TYPE_OBJECT, _('Django Object')),
        (TYPE_ENUM, _('Multiple Choice')),
        (TYPE_JSON, _('JSON Object')),
        (TYPE_CSV, _('Comma-Separated-Value')),
    )

    # Core attributes
    id = get_pk_format()

    datatype = EavDatatypeField(
        choices=DATATYPE_CHOICES,
        max_length=6,
        verbose_name=_('Data Type'),
    )

    name = models.CharField(
        max_length=CHARFIELD_LENGTH,
        help_text=_('User-friendly attribute name'),
        verbose_name=_('Name'),
    )

    """
    Main identifer for the attribute.
    Upon creation, slug is autogenerated from the name.
    (see :meth:`~eav.fields.EavSlugField.create_slug_from_name`).
    """
    slug = models.SlugField(
        max_length=SLUGFIELD_MAX_LENGTH,
        db_index=True,
        unique=True,
        help_text=_('Short unique attribute label'),
        verbose_name=_('Slug'),
    )

    """
    .. warning::
        This attribute should be used with caution. Setting this to *True*
        means that *all* entities that *can* have this attribute will
        be required to have a value for it.
    """
    required = models.BooleanField(
        default=False,
        verbose_name=_('Required'),
    )

    entity_ct = models.ManyToManyField(
        ContentType,
        blank=True,
        verbose_name=_('Entity content type'),
    )
    """
    This field allows you to specify a relationship with any number of content types.
    This would be useful, for example, if you wanted an attribute to apply only to
    a subset of entities. In that case, you could filter by content type in the
    :meth:`~eav.registry.EavConfig.get_attributes` method of that entity's config.
    """

    enum_group = models.ForeignKey(
        EnumGroup,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name=_('Choice Group'),
    )

    description = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text=_('Short description'),
        verbose_name=_('Description'),
    )

    # Useful meta-information

    display_order = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Display order'),
    )

    modified = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified'),
    )

    created = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name=_('Created'),
    )

    def natural_key(self) -> Tuple[str, str]:
        """
        Retrieve the natural key for the Attribute instance.

        The natural key for an Attribute is defined by its `name` and `slug`. This method
        returns a tuple containing these two attributes of the instance.

        Returns:
            tuple: A tuple containing the name and slug of the Attribute instance.
        """
        return (
            self.name,
            self.slug,
        )

    @property
    def help_text(self):
        return self.description

    def get_validators(self):
        """
        Returns the appropriate validator function from :mod:`~eav.validators`
        as a list (of length one) for the datatype.

        .. note::
           The reason it returns it as a list, is eventually we may want this
           method to look elsewhere for additional attribute specific
           validators to return as well as the default, built-in one.
        """
        DATATYPE_VALIDATORS = {
            'text': validate_text,
            'float': validate_float,
            'int': validate_int,
            'date': validate_date,
            'bool': validate_bool,
            'object': validate_object,
            'enum': validate_enum,
            'json': validate_json,
            'csv': validate_csv,
        }

        return [DATATYPE_VALIDATORS[self.datatype]]

    def validate_value(self, value):
        """
        Check *value* against the validators returned by
        :meth:`get_validators` for this attribute.
        """
        for validator in self.get_validators():
            validator(value)

        if self.datatype == self.TYPE_ENUM:
            if isinstance(value, EnumValue):
                value = value.value
            if not self.enum_group.values.filter(value=value).exists():
                raise ValidationError(
                    _('%(val)s is not a valid choice for %(attr)s')
                    % dict(val=value, attr=self)
                )

    def save(self, *args, **kwargs):
        """
        Saves the Attribute and auto-generates a slug field
        if one wasn't provided.
        """
        if not self.slug:
            self.slug = generate_slug(self.name)

        self.full_clean()
        super(Attribute, self).save(*args, **kwargs)

    def clean(self):
        """
        Validates the attribute.  Will raise ``ValidationError`` if the
        attribute's datatype is *TYPE_ENUM* and enum_group is not set, or if
        the attribute is not *TYPE_ENUM* and the enum group is set.
        """
        if self.datatype == self.TYPE_ENUM and not self.enum_group:
            raise ValidationError(
                _('You must set the choice group for multiple choice attributes')
            )

        if self.datatype != self.TYPE_ENUM and self.enum_group:
            raise ValidationError(
                _('You can only assign a choice group to multiple choice attributes')
            )

    def get_choices(self):
        """
        Returns a query set of :class:`EnumValue` objects for this attribute.
        Returns None if the datatype of this attribute is not *TYPE_ENUM*.
        """
        return (
            self.enum_group.values.all()
            if self.datatype == Attribute.TYPE_ENUM
            else None
        )

    def save_value(self, entity, value):
        """
        Called with *entity*, any Django object registered with eav, and
        *value*, the :class:`Value` this attribute for *entity* should
        be set to.

        If a :class:`Value` object for this *entity* and attribute doesn't
        exist, one will be created.

        .. note::
           If *value* is None and a :class:`Value` object exists for this
           Attribute and *entity*, it will delete that :class:`Value` object.
        """
        ct = ContentType.objects.get_for_model(entity)

        entity_filter = {
            'entity_ct': ct,
            'attribute': self,
            '{0}'.format(get_entity_pk_type(entity)): entity.pk,
        }

        try:
            value_obj = self.value_set.get(**entity_filter)
        except Value.DoesNotExist:
            if value == None or value == '':
                return

            value_obj = Value.objects.create(**entity_filter)

        if value == None or value == '':
            value_obj.delete()
            return

        if value != value_obj.value:
            value_obj.value = value
            value_obj.save()

    def __str__(self):
        return '{} ({})'.format(self.name, self.get_datatype_display())


class Value(models.Model):  # noqa: WPS110
    """Putting the **V** in *EAV*.

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
    attribute = models.ForeignKey(
        Attribute,
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

    entity_ct = models.ForeignKey(
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

    value_enum = models.ForeignKey(
        EnumValue,
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

    generic_value_ct = models.ForeignKey(
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

        Returns:
            tuple: A tuple containing the natural key of the attribute, entity ID,
                and entity UUID of the Value instance.
        """
        return (self.attribute.natural_key(), self.entity_id, self.entity_uuid)

    def __str__(self):
        """String representation of a Value."""
        entity = self.entity_pk_uuid if self.entity_uuid else self.entity_pk_int
        return '{0}: "{1}" ({2})'.format(
            self.attribute.name,
            self.value,
            entity,
        )

    def __repr__(self):
        """Representation of Value object."""
        entity = self.entity_pk_uuid if self.entity_uuid else self.entity_pk_int
        return '{0}: "{1}" ({2})'.format(
            self.attribute.name,
            self.value,
            entity,
        )

    def save(self, *args, **kwargs):
        """Validate and save this value."""
        self.full_clean()
        super().save(*args, **kwargs)

    def _get_value(self):
        """Return the python object this value is holding."""
        return getattr(self, 'value_{0}'.format(self.attribute.datatype))

    def _set_value(self, new_value):
        """Set the object this value is holding."""
        setattr(self, 'value_{0}'.format(self.attribute.datatype), new_value)

    value = property(_get_value, _set_value)  # noqa: WPS110


class Entity(object):
    """
    The helper class that will be attached to any entity
    registered with eav.
    """

    @staticmethod
    def pre_save_handler(sender, *args, **kwargs):
        """
        Pre save handler attached to self.instance.  Called before the
        model instance we are attached to is saved. This allows us to call
        :meth:`validate_attributes` before the entity is saved.
        """
        instance = kwargs['instance']
        entity = getattr(kwargs['instance'], instance._eav_config_cls.eav_attr)
        entity.validate_attributes()

    @staticmethod
    def post_save_handler(sender, *args, **kwargs):
        """
        Post save handler attached to self.instance.  Calls :meth:`save` when
        the model instance we are attached to is saved.
        """
        instance = kwargs['instance']
        entity = getattr(instance, instance._eav_config_cls.eav_attr)
        entity.save()

    def __init__(self, instance):
        """
        Set self.instance equal to the instance of the model that we're attached
        to. Also, store the content type of that instance.
        """
        self.instance = instance
        self.ct = ContentType.objects.get_for_model(instance)

    def __getattr__(self, name):
        """
        Tha magic getattr helper. This is called whenever user invokes::

            instance.<attribute>

        Checks if *name* is a valid slug for attributes available to this
        instances. If it is, tries to lookup the :class:`Value` with that
        attribute slug. If there is one, it returns the value of the
        class:`Value` object, otherwise it hasn't been set, so it returns
        None.
        """
        if not name.startswith('_'):
            try:
                attribute = self.get_attribute_by_slug(name)
            except Attribute.DoesNotExist:
                raise AttributeError(
                    _('%(obj)s has no EAV attribute named %(attr)s')
                    % dict(obj=self.instance, attr=name)
                )

            try:
                return self.get_value_by_attribute(attribute).value
            except Value.DoesNotExist:
                return None

        return getattr(super(Entity, self), name)

    def get_all_attributes(self):
        """
        Return a query set of all :class:`Attribute` objects that can be set
        for this entity.
        """
        return self.instance._eav_config_cls.get_attributes(
            instance=self.instance
        ).order_by('display_order')

    def _hasattr(self, attribute_slug):
        """
        Since we override __getattr__ with a backdown to the database, this
        exists as a way of checking whether a user has set a real attribute on
        ourselves, without going to the db if not.
        """
        return attribute_slug in self.__dict__

    def _getattr(self, attribute_slug):
        """
        Since we override __getattr__ with a backdown to the database, this
        exists as a way of getting the value a user set for one of our
        attributes, without going to the db to check.
        """
        return self.__dict__[attribute_slug]

    def save(self):
        """
        Saves all the EAV values that have been set on this entity.
        """
        for attribute in self.get_all_attributes():
            if self._hasattr(attribute.slug):
                attribute_value = self._getattr(attribute.slug)
                if attribute.datatype == Attribute.TYPE_ENUM and not isinstance(
                    attribute_value, EnumValue
                ):
                    if attribute_value is not None:
                        attribute_value = EnumValue.objects.get(value=attribute_value)
                attribute.save_value(self.instance, attribute_value)

    def validate_attributes(self):
        """
        Called before :meth:`save`, first validate all the entity values to
        make sure they can be created / saved cleanly.
        Raises ``ValidationError`` if they can't be.
        """
        values_dict = self.get_values_dict()

        for attribute in self.get_all_attributes():
            value = None

            # Value was assigned to this instance.
            if self._hasattr(attribute.slug):
                value = self._getattr(attribute.slug)
                values_dict.pop(attribute.slug, None)
            # Otherwise try pre-loaded from DB.
            else:
                value = values_dict.pop(attribute.slug, None)

            if value is None:
                if attribute.required:
                    raise ValidationError(
                        _('{} EAV field cannot be blank'.format(attribute.slug))
                    )
            else:
                try:
                    attribute.validate_value(value)
                except ValidationError as e:
                    raise ValidationError(
                        _('%(attr)s EAV field %(err)s')
                        % dict(attr=attribute.slug, err=e)
                    )

        illegal = values_dict or (
            self.get_object_attributes() - self.get_all_attribute_slugs()
        )

        if illegal:
            raise IllegalAssignmentException(
                'Instance of the class {} cannot have values for attributes: {}.'.format(
                    self.instance.__class__, ', '.join(illegal)
                )
            )

    def get_values_dict(self):
        return {v.attribute.slug: v.value for v in self.get_values()}

    def get_values(self):
        """Get all set :class:`Value` objects for self.instance."""
        entity_filter = {
            'entity_ct': self.ct,
            '{0}'.format(get_entity_pk_type(self.instance)): self.instance.pk,
        }

        return Value.objects.filter(**entity_filter).select_related()

    def get_all_attribute_slugs(self):
        """
        Returns a list of slugs for all attributes available to this entity.
        """
        return set(self.get_all_attributes().values_list('slug', flat=True))

    def get_attribute_by_slug(self, slug):
        """
        Returns a single :class:`Attribute` with *slug*.
        """
        return self.get_all_attributes().get(slug=slug)

    def get_value_by_attribute(self, attribute):
        """
        Returns a single :class:`Value` for *attribute*.
        """
        return self.get_values().get(attribute=attribute)

    def get_object_attributes(self):
        """
        Returns entity instance attributes, except for
        ``instance`` and ``ct`` which are used internally.
        """
        return set(copy(self.__dict__).keys()) - set(['instance', 'ct'])

    def __iter__(self):
        """
        Iterate over set eav values. This would allow you to do::

            for i in m.eav: print(i)
        """
        return iter(self.get_values())


class EAVModelMeta(ModelBase):
    def __new__(cls, name, bases, namespace, **kwds):
        result = super(EAVModelMeta, cls).__new__(cls, name, bases, dict(namespace))
        register(result)
        return result
