#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
#
#    This software is derived from EAV-Django originally written and
#    copyrighted by Andrey Mikhaylenko <http://pypi.python.org/pypi/eav-django>
#
#    This is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This software is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with EAV-Django.  If not, see <http://gnu.org/licenses/>.
'''
******
models
******
This module defines the four concrete, non-abstract models:

* :class:`Value`
* :class:`Attribute`
* :class:`EnumValue`
* :class:`EnumGroup`

Along with the :class:`Entity` helper class.

Classes
-------
'''


from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields as generic
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.conf import settings

from .validators import *
from .fields import EavSlugField, EavDatatypeField


class EnumValue(models.Model):
    '''
    *EnumValue* objects are the value 'choices' to multiple choice
    *TYPE_ENUM* :class:`Attribute` objects.

    They have only one field, *value*, a``CharField`` that must be unique.

    For example:

    >>> yes = EnumValue.objects.create(value='Yes') # doctest: SKIP
    >>> no = EnumValue.objects.create(value='No')
    >>> unkown = EnumValue.objects.create(value='Unkown')

    >>> ynu = EnumGroup.objects.create(name='Yes / No / Unkown')
    >>> ynu.enums.add(yes, no, unkown)

    >>> Attribute.objects.create(name='Has Fever?',
    ...                          datatype=Attribute.TYPE_ENUM,
    ...                          enum_group=ynu)
    <Attribute: Has the fever? (Multiple Choice)>

    .. note::
       The same *EnumValue* objects should be reused within multiple
       *EnumGroups*.  For example, if you have one *EnumGroup*
       called: *Yes / No / Unkown* and another called *Yes / No /
       Not applicable*, you should only have a total of four *EnumValues*
       objects, as you should have used the same *Yes* and *No* *EnumValues*
       for both *EnumGroups*.
    '''
    value = models.CharField(_(u"value"), db_index=True,
                             unique=True, max_length=50)

    def __unicode__(self):
        return self.value


class EnumGroup(models.Model):
    '''
    *EnumGroup* objects have two fields- a *name* ``CharField`` and *enums*,
    a ``ManyToManyField`` to :class:`EnumValue`. :class:`Attribute` classes
    with datatype *TYPE_ENUM* have a ``ForeignKey`` field to *EnumGroup*.

    See :class:`EnumValue` for an example.

    '''
    name = models.CharField(_(u"name"), unique=True, max_length=100)

    enums = models.ManyToManyField(EnumValue, verbose_name=_(u"enum group"))

    def __unicode__(self):
        return self.name


class Attribute(models.Model):
    '''
    Putting the **A** in *EAV*. This holds the attributes, or concepts.
    Examples of possible *Attributes*: color, height, weight,
    number of children, number of patients, has fever?, etc...

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

    Examples:

    >>> Attribute.objects.create(name='Height', datatype=Attribute.TYPE_INT)
    <Attribute: Height (Integer)>

    >>> Attribute.objects.create(name='Color', datatype=Attribute.TYPE_TEXT)
    <Attribute: Color (Text)>

    >>> yes = EnumValue.objects.create(value='yes')
    >>> no = EnumValue.objects.create(value='no')
    >>> unkown = EnumValue.objects.create(value='unkown')
    >>> ynu = EnumGroup.objects.create(name='Yes / No / Unkown')
    >>> ynu.enums.add(yes, no, unkown)
    >>> Attribute.objects.create(name='Has Fever?',
    ...                          datatype=Attribute.TYPE_ENUM,
    ...                          enum_group=ynu)
    <Attribute: Has Fever? (Multiple Choice)>

    .. warning:: Once an Attribute has been used by an entity, you can not
                 change it's datatype.
    '''

    class Meta:
        ordering = ['content_type', 'name']
        unique_together = ('site', 'content_type', 'slug')

    TYPE_TEXT = 'text'
    TYPE_FLOAT = 'float'
    TYPE_INT = 'int'
    TYPE_DATE = 'date'
    TYPE_BOOLEAN = 'bool'
    TYPE_OBJECT = 'object'
    TYPE_ENUM = 'enum'

    DATATYPE_CHOICES = (
        (TYPE_TEXT, _(u"Text")),
        (TYPE_FLOAT, _(u"Float")),
        (TYPE_INT, _(u"Integer")),
        (TYPE_DATE, _(u"Date")),
        (TYPE_BOOLEAN, _(u"True / False")),
        (TYPE_OBJECT, _(u"Django Object")),
        (TYPE_ENUM, _(u"Multiple Choice")),
    )

    name = models.CharField(_(u"name"), max_length=100,
                            help_text=_(u"User-friendly attribute name"))

    content_type = models.ForeignKey(ContentType,
                            blank=True, null=True,
                            verbose_name=_(u"content type"))

    site = models.ForeignKey(Site, verbose_name=_(u"site"),
                             default=settings.SITE_ID)

    slug = EavSlugField(_(u"slug"), max_length=50, db_index=True,
                          help_text=_(u"Short unique attribute label"))

    description = models.CharField(_(u"description"), max_length=256,
                                     blank=True, null=True,
                                     help_text=_(u"Short description"))

    enum_group = models.ForeignKey(EnumGroup, verbose_name=_(u"choice group"),
                                   blank=True, null=True)

    type = models.CharField(_(u"type"), max_length=20, blank=True, null=True)

    @property
    def help_text(self):
        return self.description

    datatype = EavDatatypeField(_(u"data type"), max_length=6,
                                choices=DATATYPE_CHOICES)

    created = models.DateTimeField(_(u"created"), default=timezone.now,
                                   editable=False)

    modified = models.DateTimeField(_(u"modified"), auto_now=True)

    required = models.BooleanField(_(u"required"), default=False)

    display_order = models.PositiveIntegerField(_(u"display order"), default=1)

    objects = models.Manager()
    on_site = CurrentSiteManager()

    def get_validators(self):
        '''
        Returns the appropriate validator function from :mod:`~eav.validators`
        as a list (of length one) for the datatype.

        .. note::
           The reason it returns it as a list, is eventually we may want this
           method to look elsewhere for additional attribute specific
           validators to return as well as the default, built-in one.
        '''
        DATATYPE_VALIDATORS = {
            'text': validate_text,
            'float': validate_float,
            'int': validate_int,
            'date': validate_date,
            'bool': validate_bool,
            'object': validate_object,
            'enum': validate_enum,
        }

        validation_function = DATATYPE_VALIDATORS[self.datatype]
        return [validation_function]

    def validate_value(self, value):
        '''
        Check *value* against the validators returned by
        :meth:`get_validators` for this attribute.
        '''
        for validator in self.get_validators():
            validator(value)
        if self.datatype == self.TYPE_ENUM:
            if value not in self.enum_group.enums.all():
                raise ValidationError(_(u"%(enum)s is not a valid choice "
                                        u"for %(attr)s") % \
                                       {'enum': value, 'attr': self})

    def save(self, *args, **kwargs):
        '''
        Saves the Attribute and auto-generates a slug field if one wasn't
        provided.
        '''
        if not self.slug:
            self.slug = EavSlugField.create_slug_from_name(self.name)
        self.full_clean()
        super(Attribute, self).save(*args, **kwargs)

    def clean(self):
        '''
        Validates the attribute.  Will raise ``ValidationError`` if
        the attribute's datatype is *TYPE_ENUM* and enum_group is not set,
        or if the attribute is not *TYPE_ENUM* and the enum group is set.
        '''
        if self.datatype == self.TYPE_ENUM and not self.enum_group:
            raise ValidationError(_(
                u"You must set the choice group for multiple choice" \
                u"attributes"))

        if self.datatype != self.TYPE_ENUM and self.enum_group:
            raise ValidationError(_(
                u"You can only assign a choice group to multiple choice " \
                u"attributes"))

    def get_choices(self):
        '''
        Returns a query set of :class:`EnumValue` objects for this attribute.
        Returns None if the datatype of this attribute is not *TYPE_ENUM*.
        '''
        if not self.datatype == Attribute.TYPE_ENUM:
            return None
        return self.enum_group.enums.all()

    def save_value(self, entity, value):
        '''
        Called with *entity*, any django object registered with eav, and
        *value*, the :class:`Value` this attribute for *entity* should
        be set to.

        If a :class:`Value` object for this *entity* and attribute doesn't
        exist, one will be created.

        .. note::
           If *value* is None and a :class:`Value` object exists for this
            Attribute and *entity*, it will delete that :class:`Value` object.
        '''
        ct = ContentType.objects.get_for_model(entity)
        try:
            value_obj = self.value_set.get(entity_ct=ct,
                                           entity_id=entity.pk,
                                           attribute=self)
        except Value.DoesNotExist:
            if value == None or value == '':
                return
            value_obj = Value.objects.create(entity_ct=ct,
                                             entity_id=entity.pk,
                                             attribute=self)
        if value == None or value == '':
            value_obj.delete()
            return

        if value != value_obj.value:
            value_obj.value = value
            value_obj.save()

    def __unicode__(self):
        return u"%s.%s (%s)" % (self.content_type, self.name, self.get_datatype_display())


class Value(models.Model):
    '''
    Putting the **V** in *EAV*. This model stores the value for one particular
    :class:`Attribute` for some entity.

    As with most EAV implementations, most of the columns of this model will
    be blank, as onle one *value_* field will be used.

    Example:

    >>> import eav
    >>> from django.contrib.auth.models import User
    >>> eav.register(User)
    >>> u = User.objects.create(username='crazy_dev_user')
    >>> a = Attribute.objects.create(name='Favorite Drink', datatype='text',
    ... slug='fav_drink')
    >>> Value.objects.create(entity=u, attribute=a, value_text='red bull')
    <Value: crazy_dev_user - Favorite Drink: "red bull">
    '''

    entity_ct = models.ForeignKey(ContentType, related_name='value_entities')
    entity_id = models.IntegerField()
    entity = generic.GenericForeignKey(ct_field='entity_ct',
                                       fk_field='entity_id')

    value_text = models.TextField(blank=True, null=True)
    value_float = models.FloatField(blank=True, null=True)
    value_int = models.IntegerField(blank=True, null=True)
    value_date = models.DateTimeField(blank=True, null=True)
    value_bool = models.NullBooleanField(blank=True, null=True)
    value_enum = models.ForeignKey(EnumValue, blank=True, null=True,
                                   related_name='eav_values')

    generic_value_id = models.IntegerField(blank=True, null=True)
    generic_value_ct = models.ForeignKey(ContentType, blank=True, null=True,
                                         related_name='value_values')
    value_object = generic.GenericForeignKey(ct_field='generic_value_ct',
                                             fk_field='generic_value_id')

    created = models.DateTimeField(_(u"created"), default=timezone.now)
    modified = models.DateTimeField(_(u"modified"), auto_now=True)

    attribute = models.ForeignKey(Attribute, db_index=True,
                                  verbose_name=_(u"attribute"))

    def save(self, *args, **kwargs):
        '''
        Validate and save this value
        '''
        self.full_clean()
        super(Value, self).save(*args, **kwargs)

    def clean(self):
        '''
        Raises ``ValidationError`` if this value's attribute is *TYPE_ENUM*
        and value_enum is not a valid choice for this value's attribute.
        '''
        if self.attribute.datatype == Attribute.TYPE_ENUM and \
           self.value_enum:
            if self.value_enum not in self.attribute.enum_group.enums.all():
                raise ValidationError(_(u"%(choice)s is not a valid " \
                                        u"choice for %s(attribute)") % \
                                        {'choice': self.value_enum,
                                         'attribute': self.attribute})

    def _get_value(self):
        '''
        Return the python object this value is holding
        '''
        return getattr(self, 'value_%s' % self.attribute.datatype)

    def _set_value(self, new_value):
        '''
        Set the object this value is holding
        '''
        setattr(self, 'value_%s' % self.attribute.datatype, new_value)

    value = property(_get_value, _set_value)

    def __unicode__(self):
        return u"%s - %s: \"%s\"" % (self.entity, self.attribute.name,
                                     self.value)


class Entity(object):
    '''
    The helper class that will be attached to any entity registered with
    eav.
    '''

    def __init__(self, instance):
        '''
        Set self.model equal to the instance of the model that we're attached
        to.  Also, store the content type of that instance.
        '''
        self.model = instance
        self.ct = ContentType.objects.get_for_model(instance)

    def __getattr__(self, name):
        '''
        Tha magic getattr helper.  This is called whenevery you do
        this_instance.<whatever>

        Checks if *name* is a valid slug for attributes available to this
        instances. If it is, tries to lookup the :class:`Value` with that
        attribute slug. If there is one, it returns the value of the
        class:`Value` object, otherwise it hasn't been set, so it returns
        None.
        '''
        if not name.startswith('_'):
            try:
                attribute = self.get_attribute_by_slug(name)
            except Attribute.DoesNotExist:
                raise AttributeError(_(u"%(obj)s has no EAV attribute named " \
                                       u"'%(attr)s'") % \
                                     {'obj': self.model, 'attr': name})
            try:
                return self.get_value_by_attribute(attribute).value
            except Value.DoesNotExist:
                return None
        return getattr(super(Entity, self), name)

    def get_all_attributes(self):
        '''
        Return a query set of all :class:`Attribute` objects that can be set
        for this entity.
        '''
        return self.model._eav_config_cls.get_attributes().filter(
            models.Q(content_type__isnull=True) | models.Q(content_type=self.ct)).order_by('display_order')

    def _hasattr(self, attribute_slug):
        '''
        Since we override __getattr__ with a backdown to the database, this exists as a way of
        checking whether a user has set a real attribute on ourselves, without going to the db if not
        '''
        return attribute_slug in self.__dict__

    def _getattr(self, attribute_slug):
        '''
        Since we override __getattr__ with a backdown to the database, this exists as a way of
        getting the value a user set for one of our attributes, without going to the db to check
        '''
        return self.__dict__[attribute_slug]

    def save(self):
        '''
        Saves all the EAV values that have been set on this entity.
        '''
        for attribute in self.get_all_attributes():
            if self._hasattr(attribute.slug):
                attribute_value = self._getattr(attribute.slug)
                attribute.save_value(self.model, attribute_value)

    def validate_attributes(self):
        '''
        Called before :meth:`save`, first validate all the entity values to
        make sure they can be created / saved cleanly.

        Raise ``ValidationError`` if they can't be.
        '''
        values_dict = self.get_values_dict()

        for attribute in self.get_all_attributes():
            value = None
            if self._hasattr(attribute.slug):
                value = self._getattr(attribute.slug)
            else:
                value = values_dict.get(attribute.slug, None)

            if value is None:
                if attribute.required:
                    raise ValidationError(_(u"%(attr)s EAV field cannot " \
                                                u"be blank") % \
                                              {'attr': attribute.slug})
            else:
                try:
                    attribute.validate_value(value)
                except ValidationError as e:
                    raise ValidationError(_(u"%(attr)s EAV field %(err)s") % \
                                              {'attr': attribute.slug,
                                               'err': e})

    def get_values_dict(self):
        values_dict = dict()
        for value in self.get_values():
            values_dict[value.attribute.slug] = value.value

        return values_dict

    def get_values(self):
        '''
        Get all set :class:`Value` objects for self.model
        '''
        return Value.objects.filter(entity_ct=self.ct,
                                    entity_id=self.model.pk).select_related()

    def get_all_attribute_slugs(self):
        '''
        Returns a list of slugs for all attributes available to this entity.
        '''
        return self.get_all_attributes().values_list('slug', flat=True)

    def get_attribute_by_slug(self, slug):
        '''
        Returns a single :class:`Attribute` with *slug*
        '''
        return self.get_all_attributes().get(slug=slug)

    def get_value_by_attribute(self, attribute):
        '''
        Returns a single :class:`Value` for *attribute*
        '''
        return self.get_values().get(attribute=attribute)

    def __iter__(self):
        '''
        Iterate over set eav values.

        This would allow you to do:

        >>> for i in m.eav: print i # doctest:SKIP
        '''
        return iter(self.get_values())

    @staticmethod
    def post_save_handler(sender, *args, **kwargs):
        '''
        Post save handler attached to self.model.  Calls :meth:`save` when
        the model instance we are attached to is saved.
        '''
        instance = kwargs['instance']
        entity = getattr(instance, instance._eav_config_cls.eav_attr)
        entity.save()

    @staticmethod
    def pre_save_handler(sender, *args, **kwargs):
        '''
        Pre save handler attached to self.model.  Called before the
        model instance we are attached to is saved. This allows us to call
        :meth:`validate_attributes` before the entity is saved.
        '''
        instance = kwargs['instance']
        entity = getattr(kwargs['instance'], instance._eav_config_cls.eav_attr)
        entity.validate_attributes()

if 'django_nose' in settings.INSTALLED_APPS:
    '''
    The django_nose test runner won't automatically create our Patient model
    database table which is required for tests, unless we import it here.

    Please, someone tell me a better way to do this.
    '''
    from .tests.models import Patient, Encounter
