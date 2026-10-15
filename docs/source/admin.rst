Admin integration
=================

Django EAV 2 adds an entity's attributes to its Django admin form, so staff can
edit them next to the model's regular fields.

Enable it for a model
---------------------

Use :class:`~eav.forms.BaseDynamicEntityForm` for the form and
:class:`~eav.admin.BaseEntityAdmin` for the admin class:

.. code-block:: python

    from django.contrib import admin

    from eav.admin import BaseEntityAdmin
    from eav.forms import BaseDynamicEntityForm

    class PatientAdminForm(BaseDynamicEntityForm):
        class Meta:
            model = Patient
            fields = "__all__"

    class PatientAdmin(BaseEntityAdmin):
        form = PatientAdminForm

    admin.site.register(Patient, PatientAdmin)

The attributes appear as a separate fieldset after the model's own fieldsets.
This works with the default fieldsets and with ones you define.

Each attribute becomes a form field that matches its datatype:

.. list-table::
    :header-rows: 1
    :widths: 20 40

    * - Datatype
      - Form field
    * - ``text``
      - ``CharField``
    * - ``float``
      - ``FloatField``
    * - ``int``
      - ``IntegerField``
    * - ``date``
      - ``SplitDateTimeField``
    * - ``bool``
      - ``BooleanField``
    * - ``enum``
      - ``ChoiceField``
    * - ``json`` (deprecated)
      - ``JSONField``
    * - ``csv`` (deprecated)
      - ``CSVFormField``

Attributes of the deprecated ``object`` type do not get a form field. See
`Known limitations`_.

Customize the fieldset
----------------------

Set ``eav_fieldset_title`` and ``eav_fieldset_description`` on the admin
class to change how the fieldset is labeled:

.. code-block:: python

    class PatientAdmin(BaseEntityAdmin):
        form = PatientAdminForm
        eav_fieldset_title = "Clinical measurements"
        eav_fieldset_description = "Values recorded at each visit."

Known limitations
-----------------

.. warning::

    These are known problems.

* **Attributes of the deprecated object type** break the change form. The admin
  lists the attribute as a field, but the form does not build one for it, so
  rendering the form raises ``KeyError``. We do not plan to fix this, because
  3.0 removes the type. Do not use ``object`` attributes on a model that you
  edit in the admin, or hide them with
  :meth:`~eav.registry.EavConfig.get_attributes`.
* **Inlines** need work, and we plan to fix them separately.
  :class:`~eav.admin.BaseEntityInline` expects a ``form`` that is based on
  :class:`~eav.forms.BaseDynamicEntityForm`. Without one, rendering the inline
  raises ``AttributeError``. ``TabularInline`` is not
  supported either, so use ``StackedInline``.
