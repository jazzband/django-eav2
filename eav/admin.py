"""This module contains classes used for admin integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from django.contrib.admin import helpers, site
from django.contrib.admin.options import InlineModelAdmin, ModelAdmin
from django.contrib.admin.utils import flatten_fieldsets
from django.forms.models import BaseInlineFormSet
from django.utils.safestring import mark_safe

from eav.forms import BaseDynamicEntityForm
from eav.logic.entities import entity_of
from eav.models import Attribute, EnumGroup, EnumValue, Value

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import Model
    from django.forms import ModelForm
    from django.http import HttpRequest, HttpResponse

_FieldsetSpec = tuple[str | None, dict[str, Any]]
_Prepopulated = dict[str, "Sequence[str]"]


class BaseEntityAdmin(ModelAdmin):  # type: ignore[type-arg]
    """Custom admin model to support dynamic EAV fieldsets.

    Overrides the default rendering of the change form in the Django admin to
    dynamically integrate EAV fields into the form fieldsets. This approach
    allows EAV attributes to be rendered alongside standard model fields within
    the admin interface.

    Attributes:
        eav_fieldset_title (str): Title for the dynamically added EAV fieldset.
        eav_fieldset_description (str): Optional description for the EAV fieldset.
    """

    eav_fieldset_title: str = "EAV Attributes"
    eav_fieldset_description: str | None = None

    def render_change_form(  # noqa: PLR0913, PLR0917
        self,
        request: HttpRequest,
        context: dict[str, Any],
        add: bool = False,  # noqa: FBT001, FBT002
        change: bool = False,  # noqa: FBT001, FBT002
        form_url: str = "",
        obj: Model | None = None,
    ) -> HttpResponse:
        """Dynamically modifies the admin form to include EAV fields.

        Identifies EAV fields associated with the instance being edited and
        dynamically inserts them into the admin form's fieldsets. This method
        ensures EAV fields are appropriately displayed in a dedicated fieldset
        and avoids field duplication.

        Args:
            request: HttpRequest object representing the current request.
            context: Dictionary containing context data for the form template.
            add: Whether the object is being added.
            change: Whether the object is being changed.
            form_url: The URL the form is submitted to.
            obj: The object being edited, if any.

        Returns:
            HttpResponse object representing the rendered change form.
        """
        form = context["adminform"].form

        # Identify EAV fields based on the form instance's configuration.
        eav_fields = self._get_eav_fields(form.instance)

        # # Fallback to default if no EAV fields exist
        if not eav_fields:
            return super().render_change_form(
                request,
                context,
                add,
                change,
                form_url,
                obj,
            )

        # Get the non-EAV fieldsets and then append our own
        fieldsets: list[Any] = list(self.get_fieldsets(request, obj))
        fieldsets.append(self._get_eav_fieldset(eav_fields))

        # Reconstruct the admin form with updated fieldsets.
        adminform = helpers.AdminForm(
            form,
            fieldsets,
            # Clear prepopulated fields on a view-only form to avoid a crash.
            (
                self.prepopulated_fields
                if self.has_change_permission(request, obj)
                else {}
            ),
            readonly_fields=self.readonly_fields,
            model_admin=self,
        )
        media = mark_safe(context["media"] + adminform.media)  # noqa: S308
        context.update(adminform=adminform, media=media)

        return super().render_change_form(
            request,
            context,
            add,
            change,
            form_url,
            obj,
        )

    def _get_eav_fields(self, instance: Model) -> list[str]:
        """Retrieve a list of EAV field slugs for the given instance.

        Args:
            instance: The model instance for which EAV fields are determined.

        Returns:
            A list of strings representing the slugs of EAV fields.
        """
        attributes = entity_of(instance).get_all_attributes()
        return list(attributes.values_list("slug", flat=True))

    def _get_eav_fieldset(self, eav_fields: list[str]) -> _FieldsetSpec:
        """Construct an EAV Attributes fieldset for inclusion in admin form fieldsets.

        Generates a list representing a fieldset specifically for Entity-Attribute-Value
        (EAV) fields, intended to be appended to the admin form's fieldsets
        configuration. This facilitates the dynamic inclusion of EAV fields within the
        Django admin interface by creating a designated section for these attributes.

        Args:
            eav_fields (List[str]): A list of slugs representing the EAV fields to be
                included in the EAV Attributes fieldset.
        """
        return (
            self.eav_fieldset_title,
            # ``fields`` is Django's fieldset key, used by every inline too.
            {"fields": eav_fields, "description": self.eav_fieldset_description},  # noqa: WPS226
        )


class BaseEntityInlineFormSet(BaseInlineFormSet):  # type: ignore[type-arg]
    """An inline formset that correctly initializes EAV forms."""

    def add_fields(self, form: ModelForm[Any], index: int | None) -> None:
        """Attach the parent instance to the inline form and build its EAV fields."""
        if self.instance:
            setattr(form.instance, self.fk.name, self.instance)  # pyright: ignore[reportAttributeAccessIssue]
            cast("BaseDynamicEntityForm", form)._build_dynamic_fields()  # noqa: SLF001

        super().add_fields(form, index)


class BaseEntityInline(InlineModelAdmin):  # type: ignore[type-arg]
    """Inline model admin that works correctly with EAV attributes.

    Mix in the standard ``StackedInline`` class to define the formset
    representation. The form defaults to
    :class:`~eav.forms.BaseDynamicEntityForm`; set ``form`` to a subclass of it
    to customize the form, e.g.::

        class ItemInline(BaseEntityInline, StackedInline):
            model = Item
            form = forms.ItemForm

    .. warning:: ``TabularInline`` is not supported: the patched template
        this docstring used to mention is not shipped with the package. Use
        ``StackedInline``.
    """

    form = BaseDynamicEntityForm
    formset = BaseEntityInlineFormSet

    # Django's ModelAdmin API names this method, so it cannot be renamed.
    def get_formset(  # noqa: WPS615
        self,
        request: HttpRequest,
        obj: Model | None = None,
        **kwargs: Any,
    ) -> Any:
        """Build the formset from the model's fields, not from the attributes.

        The fieldsets name the attributes too, but the form class can only have
        the model's fields and the ones it declares. The form adds a field for
        each attribute when it is created.
        """
        if "fields" not in kwargs:
            # Reverse relations and other attributes are not form fields.
            model_meta = self.model._meta  # noqa: SLF001
            known = {field.name for field in model_meta.fields if field.editable}
            known.update(field.name for field in model_meta.many_to_many)
            known.update(self.form.declared_fields)
            known.update(self.get_readonly_fields(request, obj))
            names = flatten_fieldsets(self.get_fieldsets(request, obj))
            kwargs["fields"] = [name for name in names if name in known]

        return super().get_formset(request, obj, **kwargs)

    def get_fieldsets(
        self,
        request: HttpRequest,
        obj: Model | None = None,
    ) -> list[Any]:
        """Return the declared fieldsets or fields, or build them from the form."""
        if self.fieldsets:
            return list(self.fieldsets)

        if self.fields:
            return [(None, {"fields": list(self.fields)})]

        # Passing ``fields`` stops Django from calling ``get_fieldsets`` again.
        formset = self.get_formset(request, obj, fields=None)
        fk_name = self.fk_name or formset.fk.name
        instance = self.model(**({fk_name: obj} if obj else {}))
        form = formset.form(request.POST, instance=instance)

        return [(None, {"fields": list(form.fields)})]


class AttributeAdmin(ModelAdmin):  # type: ignore[type-arg]
    """Admin for :class:`~eav.models.Attribute`."""

    list_display = ("name", "slug", "datatype", "description")
    prepopulated_fields: ClassVar[_Prepopulated] = {"slug": ("name",)}  # pyright: ignore[reportGeneralTypeIssues]


site.register(Attribute, AttributeAdmin)
site.register(EnumValue)
site.register(EnumGroup)
site.register(Value)
