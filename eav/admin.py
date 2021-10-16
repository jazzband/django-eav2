"""This module contains classes used for admin integration."""

from django.contrib import admin
from django.contrib.admin.options import InlineModelAdmin, ModelAdmin
from django.forms.models import BaseInlineFormSet
from django.utils.safestring import mark_safe

from eav.models import Attribute, EnumGroup, EnumValue, Value


class BaseEntityAdmin(ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        """
        Wrapper for ``ModelAdmin.render_change_form``. Replaces standard static
        ``AdminForm`` with an EAV-friendly one. The point is that our form
        generates fields dynamically and fieldsets must be inferred from a
        prepared and validated form instance, not just the form class. Django
        does not seem to provide hooks for this purpose, so we simply wrap the
        view and substitute some data.
        """
        form = context['adminform'].form

        # Infer correct data from the form.
        fieldsets = self.fieldsets or [(None, {'fields': form.fields.keys()})]
        adminform = admin.helpers.AdminForm(form, fieldsets, self.prepopulated_fields)
        media = mark_safe(self.media + adminform.media)

        context.update(adminform=adminform, media=media)

        return super(BaseEntityAdmin, self).render_change_form(
            request, context, *args, **kwargs
        )


class BaseEntityInlineFormSet(BaseInlineFormSet):
    """
    An inline formset that correctly initializes EAV forms.
    """

    def add_fields(self, form, index):
        if self.instance:
            setattr(form.instance, self.fk.name, self.instance)
            form._build_dynamic_fields()

        super(BaseEntityInlineFormSet, self).add_fields(form, index)


class BaseEntityInline(InlineModelAdmin):
    """
    Inline model admin that works correctly with EAV attributes. You should mix
    in the standard ``StackedInline`` or ``TabularInline`` classes in order to
    define formset representation, e.g.::

        class ItemInline(BaseEntityInline, StackedInline):
            model = Item
            form = forms.ItemForm

    .. warning:: ``TabularInline`` does *not* work out of the box. There is,
        however, a patched template ``admin/edit_inline/tabular.html`` bundled
        with EAV-Django. You can copy or symlink the ``admin`` directory to
        your templates search path (see Django documentation).
    """

    formset = BaseEntityInlineFormSet

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self.declared_fieldsets

        formset = self.get_formset(request)
        fk_name = self.fk_name or formset.fk.name
        kw = {fk_name: obj} if obj else {}
        instance = self.model(**kw)
        form = formset.form(request.POST, instance=instance)

        return [(None, {'fields': form.fields.keys()})]


class AttributeAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'datatype', 'description')
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(Attribute, AttributeAdmin)
admin.site.register(EnumValue)
admin.site.register(EnumGroup)
admin.site.register(Value)
