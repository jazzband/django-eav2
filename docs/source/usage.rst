Usage
=====

This part of the documentation will take you through all of library's
usage patterns. Before you can use EAV attributes, however, you need to
register your models.

Simple Registration
-------------------

Basic registration is very simple. You can do it with :func:`~eav.register` method:

.. code-block:: python

    import eav
    eav.register(Parts)

or with decorators:

.. code-block:: python

    from eav.decorators import register_eav

    @register_eav
    class Supplier(models.Model):
        ...

Generally, if you chose the former, the most appriopriate place for the
statement would be at the bottom of your ``models.py`` or immmediately after
model definition.

Advanced Registration
---------------------

Under the hood, registration does a couple of things:

1. Attaches :class:`~eav.managers.EntityManager` to your class. By default,
   it replaces standard manager (*objects*). You can configure under which
   attribute it is accessible with :class:`~.eav.registry.EavConfig` (see below).

2. Binds your model's *post_init* signal with
   :meth:`~eav.registry.Registry.attach_eav_attr` method. It is used to
   attach :class:`~eav.models.Entity` helper object to each model instance.
   Entity, in turn, is used to retrieve, store and validate attribute values.
   By default, it's accessible under *eav* attribute:

.. code-block:: python

    part.eav.weight = 0.56
    part.save()

3. Binds your model's *pre_save* and *post_save* signals to
   :meth:`~eav.models.Entity.pre_save_handler` and
   :meth:`~eav.models.Entity.post_save_hander`, respectively.
   Those methods are responsible for validation and storage
   of attribute values.

4. Setups up generic relation to :class:`~eav.models.Value` set.
   By default, it's accessed under *eav_values*:

.. code-block:: python

    patient.eav_values.all()
    # = <QuerySet [has fever?: "True" (1), temperature: 37.7 (2)]>

5. Sets *_eav_config_cls* attribute storing model of the config class
   used by :class:`~eav.registry.Registry`. Defaults
   to :class:`~eav.registry.EavConfig`; can be overridden (see below).

With that out of the way, almost every aspect of the registration can
be customized. All available options are provided to registration
via config class: :class:`~eav.registry.EavConfig` passed to
:meth:`~eav.register`. You can change them by overriding the class and passing
it as a second argument. Available options are as follows:

1. ``manager_attr`` - Specifies manager name. Used to refer to the
   manager from Entity class, "objects" by default.
2. ``manager_only`` - Specifies whether signals and generic relation should
   be setup for the registered model.
3. ``eav_attr`` - Named of the Entity toolkit instance on the registered
   model instance. "eav" by default. See attach_eav_attr.
4. ``generic_relation_attr`` - Name of the GenericRelation to Value
   objects. "eav_values" by default.
5. ``generic_relation_related_name`` - Name of the related name for
   GenericRelation from Entity to Value. None by default. Therefore,
   if not overridden, it is not possible to query Values by Entities.

Example registration may look like:

.. code-block:: python

    class SupplierEavConfig(EavConfig):
        manager_attr = 'eav_objects'

    eav.register(supplier, SupplierEavConfig)

.. note::

    As of now, configurable registration is not supported via
    class decorator. You have to use explicit method call.

Additionally, :class:`~eav.registry.EavConfig` provides *classmethod*
:meth:`~eav.registry.EavConfig.get_attributes` which is used to determine
a set of attributes available to a given model. By default, it returns
``Attribute.objects.all()``. As usual, it can be customized:

.. code-block:: python

    from eav.models import Attribute

    class SomeModelEavConfig(EavConfig):
        @classmethod
        def get_attributes(cls):
            return Attribute.objects.filter(slug__startswith='a')

Attribute validation includes checks against illegal attribute value
assignments. This means that value assignments for attributes which are
excluded for the model are treated with
:class:`~eav.exceptions.IllegalAssignmentException`. For example (extending
previous one):

.. code-block:: python

    some_model.eav.beard = True
    some_model.save()

will throw an exception.

Creating Attributes
-------------------

Once your models are registered, you can starting creating attributes for
them. Two most important attributes of ``Attribute`` class are *slug* and
*datatype*. *slug* is a unique global identifier (there must be at most
one ``Attribute`` instance with given `slug`) and must be a valid Python
variable name, as it's used to access values for that attribute from
:class:`~eav.models.Entity` helper:

.. code-block:: python

    from eav.models import Attribute

    Attribute.objects.create(slug='color', datatype=Attribute.TYPE_TEXT)
    flower.eav.color = 'red'

    # Alternatively, assuming you're using default EntityManager:
    Attribute.objects.create(slug='color', datatype=Attribute.TYPE_TEXT)
    Flower.objects.create(name='rose', eav__color='red')

*datatype* determines type of attribute (and by extension type of value
stored in :class:`~eav.models.Value`). Available choices are:

========= ==================
  Type    Attribute Constant
========= ==================
*int*     ``TYPE_INT``
*float*   ``TYPE_FLOAT``
*text*    ``TYPE_TEXT``
*date*    ``TYPE_DATE``
*bool*    ``TYPE_BOOLEAN``
*object*  ``TYPE_OBJECT``
*enum*    ``TYPE_ENUM``
========= ==================

If you want to create an attribute with data-type *enum*, you need to provide
it with ``enum_group``:

.. code-block:: python

    from eav.models import EnumValue, EnumGroup, Attribute

    true = EnumValue.objects.create(value='Yes')
    false = EnumValue.objects.create(value='No')
    bool_group = EnumGroup.objects.create(name='Yes / No')
    bool_group.enums.add(true, false)

    Attribute.objects.create(
        name='hungry?',
        datatype=Attribute.TYPE_ENUM,
        enum_group=bool_group
    )
    # = <Attribute: hungry? (Multiple Choice)>

Finally, attribute type *object* allows to relate Django model instances
via generic foreign keys:

.. code-block:: python

    Attribute.objects.create(name='Supplier', datatype=Attribute.TYPE_OBJECT)

    steve = Supplier.objects.create(name='Steve')
    cog = Part.objects.create(name='Cog', eav__supplier=steve)

    cog.eav.supplier
    # = <Supplier: Steve (1)>

Filtering By Attributes
-----------------------

Once you've created your attributes and values for them, you can use them
to filter Django models. Django EAV 2 is using the same notation as Django's
foreign-keys:

.. code-block:: python

    Part.objects.filter(eav__weight=10)
    Part.objects.filter(eav__weight__gt=10)
    Part.objects.filter(eav__code__startswith='A')

    # Of course, you can mix them with regular queries:
    Part.objects.filter(name='Cog', eav__height=7.8)

    # Querying enums works either by enum instance or by it's text representation as follows:
    yes = EnumValue.objects.get(name='Yes')
    Part.objects.filter(eav__is_available=yes)  # via EnumValue
    Part.objects.filter(eav__is_available='yes)  # via EnumValue's value

You can use ``Q`` expressions too:

.. code-block:: python

    Patient.objects.filter(
        Q(eav__sex='male', eav__fever=no) | Q(eav__city='Nice') & Q(eav__age__gt=32)
    )

Admin Integration
-----------------

Django EAV 2 includes integration for Django's admin. As usual, you need to
register your model first:

.. code-block:: python

    from django.contrib import admin
    from eav.forms import BaseDynamicEntityForm
    from eav.admin import BaseEntityAdmin

    class PatientAdminForm(BaseDynamicEntityForm):
        model = Patient

    class PatientAdmin(BaseEntityAdmin):
        form = PatientAdminForm

    admin.site.register(Patient, PatientAdmin)
