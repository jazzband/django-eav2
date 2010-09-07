from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from .fields import UuidField


class EavAttributeLabel(models.Model):
    name = models.CharField(_(u"name"), db_index=True,
                            unique=True, max_length=100)


class EavAttribute(models.Model):
    '''
    The A model in E-A-V. This holds the 'concepts' along with the data type
    something like:

    >>> EavAttribute.objects.create(name='height', datatype='float')
    <EavAttribute: height (Float)>

    >>> EavAttribute.objects.create(name='color', datatype='text')
    <EavAttribute: color (Text)>
    '''
    class Meta:
        ordering = ['name']

    TYPE_TEXT = 'text'
    TYPE_FLOAT = 'float'
    TYPE_INT = 'int'
    TYPE_DATE = 'date'
    TYPE_BOOLEAN = 'bool'
    #TYPE_MANY = 'many'

    DATATYPE_CHOICES = (
        (TYPE_TEXT, _(u"Text")),
        (TYPE_FLOAT, _(u"Float")),
        (TYPE_INT, _(u"Integer")),
        (TYPE_DATE, _(u"Date")),
        (TYPE_BOOLEAN, _(u"True / False")),
        #(TYPE_MANY,    _('multiple choices')),
    )

    #TODO Force name to lowercase? Don't allow spaces in name
    name = models.CharField(_(u"name"), max_length=100,
                            help_text=_(u"User-friendly attribute name"))

    help_text = models.CharField(_(u"help text"), max_length=250,
                                 blank=True, null=True,
                                 help_text=_(u"Short description"))

    datatype = models.CharField(_(u"data type"), max_length=6,
                                choices=DATATYPE_CHOICES)

    uuid = UuidField(_(u"UUID"), auto=True)

    labels = models.ManyToManyField(EavAttributeLabel,
                                    verbose_name=_(u"labels"))

    def get_value_for_entity(self, entity):
        '''
        Passed any object that may be used as an 'entity' object (is linked
        to through the generic relation from some EaveValue object. Returns
        an EavValue object that has a foreignkey to self (attribute) and
        to the entity. Returns nothing if a matching EavValue object
        doesn't exist.
        '''
        ct = ContentType.objects.get_for_model(entity)
        qs = self.eavvalue_set.filter(content_type=ct, object_id=entity.pk)
        if qs.count():
            return qs[0]

    def save_value(self, entity, value):
        self._save_single_value(entity, value)

    def _save_single_value(self, entity, value=None, attribute=None):
        ct = ContentType.objects.get_for_model(entity)
        attribute = attribute or self
        try:
            eavvalue = self.eavvalue_set.get(content_type=ct,
                                             object_id=entity.pk,
                                             attribute=attribute)
        except EavValue.DoesNotExist:
            eavvalue = self.eavvalue_set.model(content_type=ct,
                                               object_id=entity.pk,
                                               attribute=attribute)
        if value != eavvalue.value:
            eavvalue.value = value
            eavvalue.save()

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.get_datatype_display())


class EavValue(models.Model):
    class Meta:
        unique_together = ('content_type', 'object_id', 'attribute',
                           'value_text', 'value_float', 'value_date',
                           'value_bool')

    content_type = models.ForeignKey(ContentType)
    object_id = models.IntegerField()
    object = generic.GenericForeignKey()

    value_text = models.TextField(blank=True, null=True)
    value_float = models.FloatField(blank=True, null=True)
    value_int = models.IntegerField(blank=True, null=True)
    value_date = models.DateTimeField(blank=True, null=True)
    value_bool = models.BooleanField(default=False)
    #value_object = generic.GenericForeignKey()

    attribute = models.ForeignKey(EavAttribute)

    def _blank(self):
        self.value_text = self.value_float = self.value_int = self.value_date = None

    def _get_value(self):
        return getattr(self, 'value_%s' % self.attribute.datatype)

    def _set_value(self, new_value):
        self._blank()
        setattr(self, 'value_%s' % self.attribute.datatype, new_value)

    value = property(_get_value, _set_value)


    def __unicode__(self):
        return u"%s - %s: \"%s\"" % (self.object, self.attribute.name, self.value)


class EavEntity(object):
    def __init__(self, instance):
        self.model = instance
        self.ct = ContentType.objects.get_for_model(instance)

    def __getattr__(self, name):
        if not name.startswith('_'):
            if name in self.get_all_attribute_names():
                attribute = self.get_attribute_by_name(name)
                value = attribute.get_value_for_entity(self.model)
                return value.value if value else None
        raise AttributeError(_(u"%s EAV does not have attribute " \
                               u"named \"%s\".") % \
                               (self.model._meta.object_name, name))

    def save(self):
        for attribute in self.get_all_attributes():
            if hasattr(self, attribute.name):
                attribute_value = getattr(self, attribute.name)
                attribute.save_value(self.model, attribute_value)

    def get_all_attributes(self):
        try:
            if self._attributes_cache is not None:
                return self._attributes_cache
        except AttributeError:
            pass

        self._attributes_cache = self.get_eav_attributes().select_related()
        self._attributes_cache_dict = dict((s.name, s) for s in self._attributes_cache)
        return self._attributes_cache

    def get_values(self):
        return EavValue.objects.filter(content_type=self.ct,
                                       object_id=self.model.pk).select_related()

    def get_all_attribute_names(self):
        if not hasattr(self, '_attributes_cache_dict'):
            self.get_all_attributes()
        return self._attributes_cache_dict.keys()

    def get_attribute_by_name(self, name):
        if not hasattr(self, '_attributes_cache_dict'):
            self.get_all_attributes()
        return self._attributes_cache_dict[name]

    def get_attribute_by_id(self, attribute_id):
        for attr in self.get_all_attributes():
            if attr.pk == attribute_id:
                return attr

    def __iter__(self):
        "Iterates over non-empty EAV attributes. Normal fields are not included."
        return self.get_values().__iter__()

    @staticmethod
    def pre_save_handler(sender, *args, **kwargs):
        kwargs['instance'].eav.save()
