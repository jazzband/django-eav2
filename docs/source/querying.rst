Querying by attributes
======================

Registered models get an :class:`~eav.queryset.EavQuerySet`, so you can
filter, exclude, order, and get entities by their attributes. Prefix the
attribute slug with ``eav__``, the way you would follow a foreign key.

Filter
------

.. code-block:: python

    # Assumes Part is registered and has weight, code, and height attributes.
    Part.objects.filter(eav__weight=10)
    Part.objects.filter(eav__weight__gt=10)
    Part.objects.filter(eav__code__startswith="A")

Mix attribute lookups with regular fields in one call:

.. code-block:: python

    Part.objects.filter(name="Cog", eav__height=7.8)

The lookups you can use depend on the attribute's datatype. They are the
lookups Django offers for the matching field: comparisons such as ``gt`` and
``lte`` for numbers and dates, ``contains`` and ``startswith`` for text, and
``isnull`` for all of them.

You can add one lookup after the slug. Chaining a second one, such as
``eav__created__year__gt``, is not supported, and it currently returns no rows
instead of raising an error.

Enum attributes accept either an ``EnumValue`` or its text:

.. code-block:: python

    yes = EnumValue.objects.get(value="Yes")

    Part.objects.filter(eav__is_available=yes)
    Part.objects.filter(eav__is_available="Yes")

An unknown slug raises ``Attribute.DoesNotExist``, so a typo does not
silently return nothing.

Combine conditions with ``Q``
-----------------------------

``Q`` objects can mix attribute and regular fields, and combine with ``&`` and
``|``:

.. code-block:: python

    from django.db.models import Q

    no = EnumValue.objects.get(value="No")

    Patient.objects.filter(
        Q(eav__sex="male", eav__fever=no) | (Q(eav__city="Nice") & Q(eav__age__gt=32))
    )

.. warning::

    Do not put ``~Q()`` on an attribute in the same ``Q`` as other conditions.
    The negation applies to single stored values, so an entity that matches
    your other conditions can slip through. Chain ``filter()`` and
    ``exclude()`` instead:

    .. code-block:: python

        Patient.objects.filter(eav__age__gt=30).exclude(eav__city="Nice")

Exclude
-------

``exclude()`` also accepts ``eav__`` lookups. Entities that have no value for
the attribute are not excluded, because the condition does not match them:

.. code-block:: python

    Patient.objects.exclude(eav__city="Nice")

Get or create
-------------

``get()`` and ``get_or_create()`` accept ``eav__`` arguments:

.. code-block:: python

    patient = Patient.objects.get(eav__city="Nice")

    patient, created = Patient.objects.get_or_create(
        name="Ada",
        eav__city="London",
    )

Order
-----

Sort by an attribute with ``order_by("eav__<slug>")``. Prefix the name with
``-`` for descending order:

.. code-block:: python

    Patient.objects.order_by("eav__age")
    Patient.objects.order_by("-eav__age")

Enum attributes sort by the text of the choice. Ordering by an ``object``
attribute is not supported and raises ``NotSupportedError``.

Read values back
----------------

``instance.eav.<slug>`` returns the value of one attribute, or ``None`` if
none is stored. ``instance.eav.get_values_dict()`` returns all of them, keyed
by slug:

.. code-block:: python

    patient.eav.age  # 40
    patient.eav.get_values_dict()  # {"age": 40, "city": "Nice"}

Reading several attributes of one entity costs two queries in total. To read
a list of entities without extra queries per row, see :doc:`performance`.

Limitations
-----------

You can filter, exclude, and order by attributes. ``values()``,
``annotate()`` and ``aggregate()`` over attributes are not supported.
