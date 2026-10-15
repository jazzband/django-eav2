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
    * - ``json``
      - ``JSONField``
    * - ``csv``
      - ``CSVFormField``

Attributes of type ``object`` are not shown in forms.

Customize the fieldset
----------------------

Set ``eav_fieldset_title`` and ``eav_fieldset_description`` on the admin
class to change how the fieldset is labeled:

.. code-block:: python

    class PatientAdmin(BaseEntityAdmin):
        form = PatientAdminForm
        eav_fieldset_title = "Clinical measurements"
        eav_fieldset_description = "Values recorded at each visit."

Use it in inlines
-----------------

For an inline whose model is also an entity, mix
:class:`~eav.admin.BaseEntityInline` into ``StackedInline``:

.. code-block:: python

    from django.contrib.admin import StackedInline

    from eav.admin import BaseEntityInline

    class EncounterInline(BaseEntityInline, StackedInline):
        model = Encounter
        form = EncounterAdminForm

.. warning::

    ``TabularInline`` is not supported. Use ``StackedInline``.
