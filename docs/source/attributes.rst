Attributes and datatypes
========================

An :class:`~eav.models.Attribute` describes one property that entities can
have. This page covers how to create attributes and what each datatype stores.

Create an attribute
-------------------

Two fields matter most:

.. list-table::
    :header-rows: 1
    :widths: 20 80

    * - Field
      - Purpose
    * - ``datatype``
      - What the attribute stores. See `Datatypes`_.
    * - ``slug``
      - A unique identifier. It should be a valid Python name, because you use
        it to read the value: ``entity.eav.<slug>``, and Django EAV 2 warns if
        it is not. If you omit it, the slug is generated from ``name``, with
        spaces and other punctuation replaced.

.. code-block:: python

    from eav.models import Attribute

    Attribute.objects.create(name="Color", datatype=Attribute.TYPE_TEXT)
    flower.eav.color = "red"

With the default manager, you can also set values when you create the entity:

.. code-block:: python

    Flower.objects.create(name="rose", eav__color="red")

Other useful fields are ``description`` (shown as help text in forms),
``required``, and ``display_order``.

.. warning::

    ``required=True`` applies to every entity that can have the attribute.
    Saving one without a value raises ``ValidationError``.

Datatypes
---------

.. list-table::
    :header-rows: 1
    :widths: 15 30 55

    * - Datatype
      - Constant
      - Stores
    * - ``int``
      - ``Attribute.TYPE_INT``
      - Whole numbers. A float is truncated.
    * - ``float``
      - ``Attribute.TYPE_FLOAT``
      - Floating-point numbers
    * - ``text``
      - ``Attribute.TYPE_TEXT``
      - Strings
    * - ``date``
      - ``Attribute.TYPE_DATE``
      - Dates and datetimes. A plain date is stored as midnight in the
        default timezone, and reading the value returns an aware
        ``datetime``.
    * - ``bool``
      - ``Attribute.TYPE_BOOLEAN``
      - ``True`` or ``False`` only
    * - ``enum``
      - ``Attribute.TYPE_ENUM``
      - One choice from a group of options. See `Enum attributes`_.
    * - ``json``
      - ``Attribute.TYPE_JSON``
      - A JSON object (a ``dict``)
    * - ``csv``
      - ``Attribute.TYPE_CSV``
      - A list of strings. See `CSV attributes`_.
    * - ``object``
      - ``Attribute.TYPE_OBJECT``
      - A reference to a saved model instance that has an integer primary key

Enum attributes
~~~~~~~~~~~~~~~

An enum attribute needs an :class:`~eav.models.EnumGroup`, which holds the
allowed :class:`~eav.models.EnumValue` choices:

.. code-block:: python

    from eav.models import Attribute, EnumGroup, EnumValue

    yes = EnumValue.objects.create(value="Yes")
    no = EnumValue.objects.create(value="No")

    group = EnumGroup.objects.create(name="Yes / No")
    group.values.add(yes, no)

    Attribute.objects.create(
        name="Fever",
        datatype=Attribute.TYPE_ENUM,
        enum_group=group,
    )

Assign either an ``EnumValue`` or its text:

.. code-block:: python

    patient.eav.fever = yes
    patient.eav.fever = "No"

JSON attributes
~~~~~~~~~~~~~~~

A JSON attribute stores a ``dict``. Assign a ``dict``, not a JSON string, which
is stored as a string. You can filter on a key:

.. code-block:: python

    Attribute.objects.create(name="Name intl", datatype=Attribute.TYPE_JSON)

    broom = Product.objects.create(
        sku="PRD00001",
        eav__name_intl={"es": "Escoba Verde", "en": "Green Broom"},
    )
    broom.eav.name_intl  # {"es": "Escoba Verde", "en": "Green Broom"}

    Product.objects.filter(eav__name_intl__has_key="es")
    Product.objects.filter(eav__name_intl__en="Green Broom")

CSV attributes
~~~~~~~~~~~~~~

A CSV attribute stores a list of strings. You can assign a list or a string
that uses ``;`` as the separator. Reload the instance before you read the value:
until then, the attribute returns what you assigned. After a reload, it returns
a list:

.. code-block:: python

    Attribute.objects.create(name="Colors", datatype=Attribute.TYPE_CSV)

    shirt = Product.objects.create(sku="PRD00001", eav__colors="red;green;blue")
    Product.objects.create(sku="PRD00002", eav__colors="")

    shirt = Product.objects.get(sku="PRD00001")
    shirt.eav.colors  # ["red", "green", "blue"]

    Product.objects.filter(eav__colors__contains="green")

An empty string stores nothing, so reading the attribute returns ``None``. To
find entities without a value, exclude those that have one:

.. code-block:: python

    Product.objects.exclude(eav__colors__isnull=False)

Object attributes
~~~~~~~~~~~~~~~~~

An object attribute links an entity to any saved model instance through a
generic foreign key:

.. code-block:: python

    Attribute.objects.create(name="Supplier", datatype=Attribute.TYPE_OBJECT)

    steve = Supplier.objects.create(name="Steve")
    cog = Part.objects.create(name="Cog", eav__supplier=steve)

    cog.eav.supplier  # <Supplier: Steve>

The linked object must already be saved, and its primary key must be an
integer. To filter on an object attribute, pass the primary key, not the
instance:

.. code-block:: python

    Part.objects.filter(eav__supplier=steve.pk)
