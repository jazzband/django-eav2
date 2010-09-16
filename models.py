import inspect
import re
from datetime import datetime

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from .fields import EavSlugField, EavDatatypeField


def get_unique_class_identifier(cls):
    """
        Return a unique identifier for a class
    """
    return '.'.join((inspect.getfile(cls), cls.__name__))


class EavAttributeLabel(models.Model):
    name = models.CharField(_(u"name"), db_index=True,
                            unique=True, max_length=100)

    def __unicode__(self):
        return self.name


class EnumValue(models.Model):
    value = models.CharField(_(u"value"), db_index=True,
                             unique=True, max_length=50)

    def __unicode__(self):
        return self.value


class EnumGroup(models.Model):
    name = models.CharField(_(u"name"), unique=True, max_length=100)

    enums = models.ManyToManyField(EnumValue, verbose_name=_(u"enum group"))

    def __unicode__(self):
        return self.name


class EavAttribute(models.Model):
    '''
    The A model in E-A-V. This holds the 'concepts' along with the data type
    something like:

    >>> EavAttribute.objects.create(name='Height', datatype='float')
    <EavAttribute: Height (Float)>

    >>> EavAttribute.objects.create(name='Color', datatype='text', slug='color')
    <EavAttribute: Color (Text)>
    '''
    class Meta:
        ordering = ['name']

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
        (TYPE_OBJECT, _(u"Python Object")),
        (TYPE_ENUM,    _(u"Multiple Choice")),
    )

    slug = EavSlugField(_(u"slug"), max_length=50, db_index=True,
                          help_text=_(u"Short unique attribute label"),
                          unique=True)

    name = models.CharField(_(u"name"), max_length=100,
                            help_text=_(u"User-friendly attribute name"))

    description = models.CharField(_(u"description"), max_length=256,
                                     blank=True, null=True,
                                     help_text=_(u"Short description"))

    enum_group = models.ForeignKey(EnumGroup, verbose_name=_(u"choice group"),
                                   blank=True, null=True)

    @property
    def help_text(self):
        return self.description

    datatype = EavDatatypeField(_(u"data type"), max_length=6,
                                choices=DATATYPE_CHOICES)

    created = models.DateTimeField(_(u"created"), default=datetime.now)

    modified = models.DateTimeField(_(u"modified"), auto_now=True)

    labels = models.ManyToManyField(EavAttributeLabel,
                                    verbose_name=_(u"labels"))


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = EavSlugField.create_slug_from_name(self.name)
        self.full_clean()
        super(EavAttribute, self).save(*args, **kwargs)

    def clean(self):
        if self.datatype == self.TYPE_ENUM and not enum_group:
            raise ValidationError(_(
                u"You must set the enum_group for TYPE_ENUM attributes"))

    def add_label(self, label):
        label, created = EavAttributeLabel.objects.get_or_create(name=label)
        label.eavattribute_set.add(self)

    def remove_label(self, label):
        try:
            label_obj = EavAttributeLabel.objects.get(name=label)
        except EavAttributeLabel.DoesNotExist:
            return
        self.labels.remove(label_obj)


    def get_value_for_entity(self, entity):
        '''
        Passed any object that may be used as an 'entity' object (is linked
        to through the generic relation from some EaveValue object. Returns
        an EavValue object that has a foreignkey to self (attribute) and
        to the entity. Returns nothing if a matching EavValue object
        doesn't exist.
        '''
        ct = ContentType.objects.get_for_model(entity)
        qs = self.eavvalue_set.filter(entity_ct=ct, entity_id=entity.pk)
        count = qs.count()
        if count > 1:
            raise AttributeError(u"You should have one and only one value "\
                             u"for the attribute %s and the entity %s. Found "\
                             u"%s" % (self, entity, qs.count()))
        if count:
            return qs[0]
            
        return None
         
         
    def save_value(self, entity, value):
        """
            Save any value for an entity, calling the appropriate method
            according to the type of the value.
            Value should not be an EavValue but a normal value
        """
        self._save_single_value(entity, value)


    def _save_single_value(self, entity, value=None, attribute=None):
        """
            Save a a value of type that doesn't need special joining like
            int, float, text, date, etc.
        
            Value should not be an EavValue object but a normal value.
            Use attribute if you want to use something else than the current
            one
        """
        ct = ContentType.objects.get_for_model(entity)
        attribute = attribute or self
        try:
            eavvalue = self.eavvalue_set.get(entity_ct=ct,
                                             entity_id=entity.pk,
                                             attribute=attribute)
        except EavValue.DoesNotExist:
            eavvalue = self.eavvalue_set.model(entity_ct=ct,
                                               entity_id=entity.pk,
                                               attribute=attribute)
        if value != eavvalue.value:
            eavvalue.value = value
            eavvalue.save()


    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.get_datatype_display())


class EavValue(models.Model):
    '''
    The V model in E-A-V. This holds the 'value' for an attribute and an
    entity:

    >>> from django.db import models
    >>> from django.contrib.auth.models import User
    >>> from .utils import EavRegistry
    >>> EavRegistry.register(User)
    >>> u = User.objects.create(username='crazy_dev_user')
    >>> a = EavAttribute.objects.create(name='Favorite Drink', datatype='text',
    ... slug='fav_drink')
    >>> EavValue.objects.create(entity=u, attribute=a, value_text='red bull')
    <EavValue: crazy_dev_user - Favorite Drink: "red bull">

    '''

    entity_ct = models.ForeignKey(ContentType, related_name='value_entities')
    entity_id = models.IntegerField()
    entity = generic.GenericForeignKey(ct_field='entity_ct', fk_field='entity_id')

    value_text = models.TextField(blank=True, null=True)
    value_float = models.FloatField(blank=True, null=True)
    value_int = models.IntegerField(blank=True, null=True)
    value_date = models.DateTimeField(blank=True, null=True)
    value_bool = models.NullBooleanField(blank=True, null=True)
    value_enum = models.ForeignKey(EnumValue, blank=True, null=True)

    generic_value_id = models.IntegerField(blank=True, null=True)
    generic_value_ct = models.ForeignKey(ContentType, blank=True, null=True,
                                         related_name='value_values')
    value_object = generic.GenericForeignKey(ct_field='generic_value_ct',
                                             fk_field='generic_value_id')

    created = models.DateTimeField(_(u"created"), default=datetime.now)
    modified = models.DateTimeField(_(u"modified"), auto_now=True)

    attribute = models.ForeignKey(EavAttribute)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(EavValue, self).save(*args, **kwargs)

    def clean(self):
        if self.attribute.datatype == EavAttribute.TYPE_ENUM and \
           self.value_enum:
            if self.value_enum not in self.attribute.enumvalues:
                raise ValidationError(_(u"%(choice)s is not a valid " \
                                        u"choice for %s(attribute)") % \
                                        {'choice': self.value_enum,
                                         'attribute': self.attribute})

    # todo: do it in a faster way (one update)
    def _blank(self):
        """
            Set all the field to none
        """
        for field in self._meta.fields:
            if field.name.startswith('value_') and field.null == True:
                setattr(self, field.name, None)


    def _get_value(self):
        """
            Get returns the Python object hold by this EavValue object.
        """
        return getattr(self, 'value_%s' % self.attribute.datatype)


    def _set_value(self, new_value):
        self._blank()
        setattr(self, 'value_%s' % self.attribute.datatype, new_value)

    value = property(_get_value, _set_value)

    def __unicode__(self):
        return u"%s - %s: \"%s\"" % (self.entity, self.attribute.name, self.value)


class EavEntity(object):

    _cache = {}

    def __init__(self, instance):
        self.model = instance
        self.ct = ContentType.objects.get_for_model(instance)


    # TODO: memoize
    def __getattr__(self, name):
    
        if not name.startswith('_'):
            attribute = self.get_attribute_by_slug(name)
            if attribute:
                value_obj = attribute.get_value_for_entity(self.model)
                if value_obj:
                    return value_obj.value
            return None
             
        return object.__getattr__(self, name)


    @classmethod   
    def get_eav_attributes_for_model(cls, model_cls):
        """
            Return the attributes for this model
        """
        from .utils import EavRegistry
        config_cls = EavRegistry.get_config_cls_for_model(model_cls)
        return config_cls.get_eav_attributes()


    @classmethod   
    def get_attr_cache_for_model(cls, model_cls):
        """
            Return the attribute cache for this model
        """
        return cls._cache.setdefault(get_unique_class_identifier(model_cls), {})


    @classmethod
    def update_attr_cache_for_model(cls, model_cls):
        """
            Create or update the attributes cache for this entity class.
        """
        cache = cls.get_attr_cache_for_model(model_cls) 
        cache['attributes'] = cls.get_eav_attributes_for_model(model_cls)\
                                 .select_related()
        cache['slug_mapping'] = dict((s.slug, s) for s in cache['attributes'])
        return cache


    @classmethod
    def flush_attr_cache_for_model(cls, model_cls):
        """
            Flush the attributes cache for this entity class
        """
        cache = cls.get_attr_cache_for_model(model_cls)
        cache.clear()
        return cache
        
    
    def get_eav_attributes(self):
        """
            Return the attributes for this model
        """
        return self.__class__.get_eav_attributes_for_model(self.model.__class__)
        

    def update_attr_cache(self):
        """
            Create or update the attributes cache for the entity class linked
            to the current instance.
        """
        return self.__class__.update_attr_cache_for_model(self.model.__class__)
        
        
    def flush_attr_cache(self):
        """
            Flush the attributes cache for the entity class linked
            to the current instance.
        """
        return self.__class__.flush_attr_cache_for_model(self.model.__class__)
        
        
    def get_attr_cache(self):
        """
            Return the attribute cache for the entity class linked
            to the current instance.
        """
        return self.__class__.get_attr_cache_for_model(self.model.__class__)


    def save(self):
        for attribute in self.get_eav_attributes():
            if hasattr(self, attribute.slug):
                attribute_value = getattr(self, attribute.slug)
                attribute.save_value(self.model, attribute_value)


    @classmethod
    def get_all_attributes_for_model(cls, model_cls):
        """
            Return the current cache or if it doesn't exists, update it
            and returns it.
        """
        cache = cls.get_attr_cache_for_model(model_cls)
        if not cache:
            cache = EavEntity.update_attr_cache_for_model(model_cls)

        return cache['attributes'] 
        

    def get_values(self):
        return EavValue.objects.filter(entity_ct=self.ct,
                                       entity_id=self.model.pk).select_related()

    @classmethod
    def get_all_attribute_slugs_for_model(cls, model_cls):
        """
            Returns all attributes slugs for the entity 
            class linked to the passed model.
        """
        cache = cls.get_attr_cache_for_model(model_cls)
        if not cache:
            cache = EavEntity.update_attr_cache_for_model(model_cls)

        return cache['slug_mapping']


    def get_all_attribute_slugs(self):
        """
            Returns all attributes slugs for the entity 
            class linked to the current instance.
        """
        m_cls = self.model.__class__
        return self.__class__.get_all_attribute_slugs_for_model(m_cls)


    @classmethod
    def get_attribute_by_slug_for_model(cls, model_cls, slug):
        """
            Returns all attributes slugs for the entity 
            class linked to the passed model.
        """
        cache = cls.get_attr_cache_for_model(model_cls)
        if not cache:
            cache = EavEntity.update_attr_cache_for_model(model_cls)
        return cache['slug_mapping'].get(slug, None)


    def get_attribute_by_slug(self, slug):
        m_cls = self.model.__class__
        return self.__class__.get_attribute_by_slug_for_model(m_cls, slug)


    def __iter__(self):
        """
            Iterates over non-empty EAV attributes. Normal fields are not included.
        """
        return iter(self.get_values())


    # todo: cache all changed value in EAV and check against existing attribtue
    @staticmethod
    def save_handler(sender, *args, **kwargs):
        from .utils import EavRegistry
        config_cls = EavRegistry.get_config_cls_for_model(sender)
        instance_eav = getattr(kwargs['instance'], config_cls.proxy_field_name)
        instance_eav.save()
        

