'''Forms. This module contains forms used for admin integration.'''

from copy import deepcopy

from django.contrib.admin.widgets import AdminSplitDateTime
from django.forms import (BooleanField, CharField, ChoiceField, DateTimeField,
                          FloatField, IntegerField, ModelForm)
from django.utils.translation import ugettext_lazy as _


class BaseDynamicEntityForm(ModelForm):
    '''
    ModelForm for entity with support for EAV attributes. Form fields are
    created on the fly depending on Schema defined for given entity instance.
    If no schema is defined (i.e. the entity instance has not been saved yet),
    only static fields are used. However, on form validation the schema will be
    retrieved and EAV fields dynamically added to the form, so when the
    validation is actually done, all EAV fields are present in it (unless
    Rubric is not defined).
    '''

    FIELD_CLASSES = {
        'text': CharField,
        'float': FloatField,
        'int': IntegerField,
        'date': DateTimeField,
        'bool': BooleanField,
        'enum': ChoiceField,
    }

    def __init__(self, data=None, *args, **kwargs):
        super(BaseDynamicEntityForm, self).__init__(data, *args, **kwargs)
        config_cls = self.instance._eav_config_cls
        self.entity = getattr(self.instance, config_cls.eav_attr)
        self._build_dynamic_fields()

    def _build_dynamic_fields(self):
        # reset form fields
        self.fields = deepcopy(self.base_fields)

        for attribute in self.entity.get_all_attributes():
            value = getattr(self.entity, attribute.slug)

            defaults = {
                'label': attribute.name.capitalize(),
                'required': attribute.required,
                'help_text': attribute.help_text,
                'validators': attribute.get_validators(),
            }

            datatype = attribute.datatype
            if datatype == attribute.TYPE_ENUM:
                enums = attribute.get_choices() \
                                 .values_list('id', 'value')

                choices = [('', '-----')] + list(enums)

                defaults.update({'choices': choices})
                if value:
                    defaults.update({'initial': value.pk})

            elif datatype == attribute.TYPE_DATE:
                defaults.update({'widget': AdminSplitDateTime})
            elif datatype == attribute.TYPE_OBJECT:
                continue

            MappedField = self.FIELD_CLASSES[datatype]
            self.fields[attribute.slug] = MappedField(**defaults)

            # fill initial data (if attribute was already defined)
            if value and not datatype == attribute.TYPE_ENUM: #enum done above
                self.initial[attribute.slug] = value

    def save(self, commit=True):
        """
        Saves this ``form``'s cleaned_data into model instance
        ``self.instance`` and related EAV attributes.

        Returns ``instance``.
        """

        if self.errors:
            raise ValueError(_(u"The %s could not be saved because the data"
                             u"didn't validate.") % \
                             self.instance._meta.object_name)

        # create entity instance, don't save yet
        instance = super(BaseDynamicEntityForm, self).save(commit=False)

        # assign attributes
        for attribute in self.entity.get_all_attributes():
            value = self.cleaned_data.get(attribute.slug)
            if attribute.datatype == attribute.TYPE_ENUM:
                if value:
                    value = attribute.enum_group.enums.get(pk=value)
                else:
                    value = None

            setattr(self.entity, attribute.slug, value)

        # save entity and its attributes
        if commit:
            instance.save()

        return instance
