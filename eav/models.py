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

from django.contrib.contenttypes import fields as generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .exceptions import IllegalAssignmentException
from .fields import EavDatatypeField, EavSlugField
from .validators import *
from . import register


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
    value = models.CharField(_('value'), db_index=True, unique=True, max_length=50)

    def __str__(self):
        return '<EnumValue {}>'.format(self.value)


class EnumGroup(models.Model):
    """
    *EnumGroup* objects have two fields - a *name* ``CharField`` and *values*,
    a ``ManyToManyField`` to :class:`EnumValue`. :class:`Attribute` classes
    with datatype *TYPE_ENUM* have a ``ForeignKey`` field to *EnumGroup*.

    See :class:`EnumValue` for an example.
    """
    name = models.CharField(_('name'), unique = True, max_length = 100)
    values = models.ManyToManyField(EnumValue, verbose_name = _('enum group'))

    def __str__(self):
        return '<EnumGroup {}>'.format(self.name)


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
    class Meta:
        ordering = ['name']

    TYPE_TEXT    = 'text'
    TYPE_FLOAT   = 'float'
    TYPE_INT     = 'int'
    TYPE_DATE    = 'date'
    TYPE_BOOLEAN = 'bool'
    TYPE_OBJECT  = 'object'
    TYPE_ENUM    = 'enum'

    DATATYPE_CHOICES = (
        (TYPE_TEXT,    _('Text')),
        (TYPE_DATE,    _('Date')),
        (TYPE_FLOAT,   _('Float')),
        (TYPE_INT,     _('Integer')),
        (TYPE_BOOLEAN, _('True / False')),
        (TYPE_OBJECT,  _('Django Object')),
        (TYPE_ENUM,    _('Multiple Choice')),
    )

    # Core attributes

    datatype = EavDatatypeField(
        verbose_name = _('Data Type'),
        choices      = DATATYPE_CHOICES,
        max_length   = 6
    )

    name = models.CharField(
        verbose_name = _('Name'),
        max_length   = 100,
        help_text    = _('User-friendly attribute name')
    )

    """
    Main identifer for the attribute.
    Upon creation, slug is autogenerated from the name.
    (see :meth:`~eav.fields.EavSlugField.create_slug_from_name`).
    """
    slug = EavSlugField(
        verbose_name = _('Slug'),
        max_length   = 50,
        db_index     = True,
        unique       = True,
        help_text    = _('Short unique attribute label')
    )

    """
    .. warning::
        This attribute should be used with caution. Setting this to *True*
        means that *all* entities that *can* have this attribute will
        be required to have a value for it.
    """
    required = models.BooleanField(verbose_name = _('Required'), default = False)

    enum_group = models.ForeignKey(
        EnumGroup,
        verbose_name = _('Choice Group'),
        on_delete    = models.PROTECT,
        blank        = True,
        null         = True
    )

    description = models.CharField(
        verbose_name = _('Description'),
        max_length   = 256,
        blank        = True,
        null         = True,
        help_text    = _('Short description')
    )

    # Useful meta-information

    display_order = models.PositiveIntegerField(
        verbose_name = _('Display order'),
        default = 1
    )

    modified = models.DateTimeField(
       verbose_name = _('Modified'),
       auto_now     = True
    )

    created = models.DateTimeField(
       verbose_name = _('Created'),
       default      = timezone.now,
       editable     = False
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
            'text':   validate_text,
            'float':  validate_float,
            'int':    validate_int,
            'date':   validate_date,
            'bool':   validate_bool,
            'object': validate_object,
            'enum':   validate_enum,
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
            if value not in self.enum_group.values.all():
                raise ValidationError(
                    _('%(val)s is not a valid choice for %(attr)s')
                    % dict(val = value, attr = self)
                )

    def save(self, *args, **kwargs):
        """
        Saves the Attribute and auto-generates a slug field
        if one wasn't provided.
        """
        if not self.slug:
            self.slug = EavSlugField.create_slug_from_name(self.name)

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
        return self.enum_group.values.all() if self.datatype == Attribute.TYPE_ENUM else None

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

        try:
            value_obj = self.value_set.get(
                entity_ct = ct,
                entity_id = entity.pk,
                attribute = self
            )
        except Value.DoesNotExist:
            if value == None or value == '':
                return

            value_obj = Value.objects.create(
                entity_ct = ct,
                entity_id = entity.pk,
                attribute = self
            )

        if value == None or value == '':
            value_obj.delete()
            return

        if value != value_obj.value:
            value_obj.value = value
            value_obj.save()

    def __str__(self):
        return '{} ({})'.format(self.name, self.get_datatype_display())


class Value(models.Model):
    """
    Putting the **V** in *EAV*. This model stores the value for one particular
    :class:`Attribute` for some entity.

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

    entity_ct = models.ForeignKey(
        ContentType,
        on_delete    = models.PROTECT,
        related_name = 'value_entities'
    )

    entity_id = models.IntegerField()
    entity = generic.GenericForeignKey(ct_field = 'entity_ct', fk_field = 'entity_id')

    value_text  = models.TextField(blank = True, null = True)
    value_float = models.FloatField(blank = True, null = True)
    value_int   = models.IntegerField(blank = True, null = True)
    value_date  = models.DateTimeField(blank = True, null = True)
    value_bool  = models.NullBooleanField(blank = True, null = True)

    value_enum  = models.ForeignKey(
        EnumValue,
        blank        = True,
        null         = True,
        on_delete    = models.PROTECT,
        related_name = 'eav_values'
    )

    generic_value_id = models.IntegerField(blank=True, null=True)

    generic_value_ct = models.ForeignKey(
        ContentType,
        blank        = True,
        null         = True,
        on_delete    = models.PROTECT,
        related_name ='value_values'
    )

    value_object = generic.GenericForeignKey(
        ct_field = 'generic_value_ct',
        fk_field = 'generic_value_id'
    )

    created = models.DateTimeField(_('Created'), default = timezone.now)
    modified = models.DateTimeField(_('Modified'), auto_now = True)

    attribute = models.ForeignKey(
        Attribute,
        db_index     = True,
        on_delete    = models.PROTECT,
        verbose_name = _('attribute')
    )

    def save(self, *args, **kwargs):
        """
        Validate and save this value.
        """
        self.full_clean()
        super(Value, self).save(*args, **kwargs)

    def clean(self):
        """
        Raises ``ValidationError`` if this value's attribute is *TYPE_ENUM*
        and value_enum is not a valid choice for this value's attribute.
        """
        if self.attribute.datatype == Attribute.TYPE_ENUM and self.value_enum:
            if self.value_enum not in self.attribute.enum_group.values.all():
                raise ValidationError(
                    _('%(enum)s is not a valid choice for %(attr)s')
                    % dict(enum = self.value_enum, attr = self.attribute)
                )

    def _get_value(self):
        """
        Return the python object this value is holding
        """
        return getattr(self, 'value_%s' % self.attribute.datatype)

    def _set_value(self, new_value):
        """
        Set the object this value is holding
        """
        setattr(self, 'value_%s' % self.attribute.datatype, new_value)

    value = property(_get_value, _set_value)

    def __str__(self):
        return '{}: "{}" ({})'.format(self.attribute.name, self.value, self.entity)

    def __repr__(self):
        return '{}: "{}" ({})'.format(self.attribute.name, self.value, self.entity.pk)


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
                    % dict(obj = self.instance, attr = name)
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
        return self.instance._eav_config_cls.get_attributes().order_by('display_order')

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
                        % dict(attr = attribute.slug, err = e)
                    )

        illegal = values_dict or (
            self.get_object_attributes() - self.get_all_attribute_slugs())

        if illegal:
            raise IllegalAssignmentException(
                'Instance of the class {} cannot have values for attributes: {}.'
                .format(self.instance.__class__, ', '.join(illegal))
            )

    def get_values_dict(self):
        return {v.attribute.slug: v.value for v in self.get_values()}

    def get_values(self):
        """
        Get all set :class:`Value` objects for self.instance
        """
        return Value.objects.filter(
            entity_ct = self.ct,
            entity_id = self.instance.pk
        ).select_related()

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
