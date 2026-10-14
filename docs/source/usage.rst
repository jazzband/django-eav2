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

Generally, if you chose the former, the most appropriate place for the
statement would be at the bottom of your ``models.py`` or immediately after
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
   :meth:`~eav.models.Entity.post_save_handler`, respectively.
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
one ``Attribute`` instance with given ``slug``) and must be a valid Python
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
*json*    ``TYPE_JSON``
*csv*     ``TYPE_CSV``
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

The attribute type *json* allows to store them in JSON format, which internally use JSONField:

.. code-block:: python

    Attribute.objects.create(name='name_intl', datatype=Attribute.TYPE_JSON)

    prod = Product.objects.create(sku='PRD00001', eav__name_intl={
        "es": "Escoba Verde",
        "en": "Green Broom",
        "it": "Scopa Verde"
    })

    prod2 = Product.objects.create(sku='PRD00002', eav__name_intl={
        "es": "Escoba Roja",
        "en": "Red Broom"
    })

    prod3 = Product.objects.create(sku='PRD00003', eav__name_intl={
        "es": "Escoba Azul",
        "it": "Scopa Blu"
    })

    prod.eav.name_intl
    {'es': 'Escoba Verde', 'en': 'Green Broom', 'it': 'Scopa Verde'}

    type(prod.eav.name_intl)
    dict

    Product.objects.filter(eav__name_intl__has_key="it")
    <EavQuerySet [<Product: PRD00001>, <Product: PRD00003>]>

The attribute type *csv* allows to store Comma Separated Values, using ";" as a separator:

.. code-block:: python

    Attribute.objects.create(name='colors', datatype=Attribute.TYPE_CSV)

    prod = Product.objects.create(sku='PRD00001', eav__colors="red;green;blue")

    prod2 = Product.objects.create(sku='PRD00002', eav__colors="red;green")

    prod3 = Product.objects.create(sku='PRD00003', eav__colors="red;blue")

    prod4 = Product.objects.create(sku='PRD00004', eav__colors="")

    prod.eav.colors
    ["red", "green", "blue"]

    type(prod.eav.name_intl)
    list

    Product.objects.filter(eav__name_colors="green")
    <EavQuerySet [<Product: PRD00001>, <Product: PRD00002>]>

    Product.objects.filter(~Q(eav__name_colors__isnull=False))
    <EavQuerySet [<Product: PRD00004>]>


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

Performance
-----------

Reading ``instance.eav.<slug>`` loads the entity's attributes and values once
and reuses them, so reading several attributes costs two queries in total
rather than two per attribute. The values are kept on the instance in the same
cache ``prefetch_related`` uses, so ``refresh_from_db()`` clears them, and so
does saving (the next read after a save loads them again). If values may have
changed elsewhere (another process, a raw query), call
``instance.eav.clear_cache()`` before reading them again.

Saving only writes the values that were assigned, and loads the attributes and
values it needs a single time.

When listing entities, prefetch their values so reading an attribute does not
query per row::

    patients = Patient.objects.prefetch_related("eav_values__attribute")

    for patient in patients:
        print(patient.eav.age)  # no extra queries

Prefetching is explicit on purpose: it loads every value of every row, which
is wasted work when a list never reads EAV attributes. Without it, a list of
``N`` entities costs ``N + 2`` queries when you read an attribute on each: the
list, one attribute lookup shared by all of them, and one query per entity for
its values. With the prefetch it is 3 queries, however long the list is.

The shared attribute lookup is only used when the model uses the default
``EavConfig.get_attributes``.

Bulk Operations
---------------

``bulk_create()`` and ``bulk_update()`` on an EAV model's manager store EAV
values too, in about one query per 1000 rows instead of one or more per
entity.
Assign values on each instance before calling them, as you would for a single
save::

    patients = []
    for name, age in rows:
        patient = Patient(name=name)
        patient.eav.age = age
        patient.eav.city = "London"
        patients.append(patient)

    Patient.objects.bulk_create(patients)

``bulk_create()`` validates every instance first (required attributes, value
types, enum choices, unknown attributes), and raises before anything is
written. The instances, then their values, are written inside one transaction,
in chunks of ``batch_size`` instances, so memory stays bounded for large
inputs. ``batch_size`` is also the most rows sent in one ``INSERT``. It is 1000
by default; set ``bulk_batch_size`` on your ``EavConfig`` to change it for a
model, or pass ``batch_size`` to override it for one call::

    class PatientConfig(EavConfig):
        bulk_batch_size = 2000

    eav.register(Patient, PatientConfig)

Larger batches mean fewer queries but bigger statements. On PostgreSQL and
MySQL anything from 500 to a few thousand performs about the same on a local
database, and the main gain over 1000 is fewer round trips on a networked one.
Keep ``batch_size`` times the number of columns under PostgreSQL's limit of
65535 bind parameters if you use server-side binding, and under MySQL's
``max_allowed_packet``. SQLite lowers it automatically to its variable limit.

To update, list EAV attributes as ``eav__<slug>`` next to ordinary fields::

    for patient in patients:
        patient.name = patient.name.title()
        patient.eav.age += 1

    Patient.objects.bulk_update(patients, ["name", "eav__age"])

Only attributes with a value assigned on the instance are written, and a value
of ``None`` or ``""`` deletes the stored value.

As with Django's bulk operations, no signals are sent: ``Value`` signal
handlers and history tracking do not run for values written this way, and
``save()`` on a single entity is unchanged. Created entities need primary keys
to link their values to: UUID primary keys always work, and so do integer keys
on PostgreSQL, SQLite and MariaDB. MySQL does not return auto-increment keys,
so use UUID keys there. ``ignore_conflicts`` and ``update_conflicts`` cannot be
combined with EAV values.

Admin Integration
-----------------

Django EAV 2 seamlessly integrates with Django's admin interface by providing
dynamic attribute management directly within the admin panel. This feature
provides the EAV Attributes as a separate fieldset, whether use the base
fieldset or when providing your own.

.. code-block:: python

    from django.contrib import admin
    from eav.forms import BaseDynamicEntityForm
    from eav.admin import BaseEntityAdmin

    class PatientAdminForm(BaseDynamicEntityForm):
        model = Patient

    class PatientAdmin(BaseEntityAdmin):
        form = PatientAdminForm

    admin.site.register(Patient, PatientAdmin)

Customizing the EAV Fieldset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Django EAV 2 integration allows you to customize the presentation of EAV
attributes in the admin interface through the use of a dedicated fieldset. You
can configure this fieldset by setting ``eav_fieldset_title`` and
``eav_fieldset_description`` within your admin class.
