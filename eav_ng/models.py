from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _


class EavEntity(object):
    """
    Should be inherited by any model you want to have EAV attributes
    """

    def __init__(self, instance):
        self.model = instance

    def get_current_eav_attributes(self):
        try:
            if self._attributes_cache is not None:
                return self._attributes_cache
        except AttributeError:
            pass
        
        all_attributes = self.get_eav_attributes().select_related()
        self._attributes_cache = self.get_schemata_for_instance(all_schemata) #continue here
        self._schemata_cache_dict = dict((s.name, s) for s in self._schemata_cache)
        print 'locals', locals()
        print 'Starting get_schemata'
        return self._schemata_cache

    @classmethod
    def get_eav_attributes(cls):
        return EavAttribute.objects.all()



class EavAttribute(models.Model):
    """

    """
    class Meta:
        ordering = ['name']

    TYPE_TEXT = 'text'
    TYPE_FLOAT = 'float'
    TYPE_INT = 'int'
    TYPE_DATE = 'date'
    TYPE_BOOLEAN = 'bool'
    #TYPE_MANY = 'many'
    #TYPE_RANGE = 'range'

    DATATYPE_CHOICES = (
        (TYPE_TEXT, _("Text")),
        (TYPE_FLOAT, _("Float")),
        (TYPE_INT, _("Integer")),
        (TYPE_DATE, _("Date")),
        (TYPE_BOOLEAN, _("True / False")),
        #(TYPE_MANY,    _('multiple choices')),
        #(TYPE_RANGE,   _('numeric range')),
    )

    name = models.CharField(_(u"name"), max_length=100,
                            help_text=_(u"user-friendly attribute name"))

    help_text = models.CharField(_(u"help text"), max_length=250,
                                 blank=True, null=True,
                                 help_text=_(u"Short description for user"))

    datatype = models.CharField(_(u"data type"), max_length=6,
                                choices=DATATYPE_CHOICES)


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
    #value_range_min = FloatField(blank=True, null=True)
    #value_range_max = FloatField(blank=True, null=True)

    attribute = models.ForeignKey(EavAttribute)

    def _get_value(self):
        return getattr(self, "value_%s" % self.attribute.datatype)

    def _set_value(self, new_value):
        setattr(self, "value_%s" % self.attribute.datatype, new_value)

    value = property(_get_value, _set_value)

    def __unicode__(self):
        return u"%s - %s: \"%s\"" % (self.object, self.attribute.name, self.value)

