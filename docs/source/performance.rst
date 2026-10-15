Performance and caching
=======================

This page explains when Django EAV 2 queries the database and how to keep the
number of queries low.

How reads are cached
--------------------

The first time you read ``instance.eav.<slug>``, the library loads the
entity's attributes and all of its values, and keeps them on the instance.
Later reads cost nothing. Reading several attributes therefore takes two
queries in total, where a query per attribute would take two for each one.

The values live in the same cache that ``prefetch_related`` uses on the
instance. Calling ``refresh_from_db()`` clears that cache. So does ``save()``:
the next read after a save loads the values again.

Reading stale values
--------------------

The cache does not notice changes made outside the instance, such as another
process, a raw query, or ``Value.objects.bulk_create()``. To read the current
values, clear the cache:

.. code-block:: python

    patient.eav.clear_cache()
    patient.eav.age  # reloaded from the database

If a model's values are mostly written that way, turn the cache off for it.
Every read and save then queries the database:

.. code-block:: python

    class PatientEavConfig(EavConfig):
        cache_values = False

    eav.register(Patient, PatientEavConfig)

``prefetch_related`` of the values has no effect on a model that turns the
cache off.

Listing many entities
---------------------

Prefetch the values when you read attributes across a list:

.. code-block:: python

    patients = Patient.objects.prefetch_related("eav_values__attribute")

    for patient in patients:
        print(patient.eav.age)  # no extra queries

Prefetching is explicit because it loads every value of every row, which is
wasted work when the list never reads attributes. The cost of reading one
attribute on each of ``N`` entities is:

.. list-table::
    :header-rows: 1
    :widths: 40 60

    * - Approach
      - Queries
    * - Without ``prefetch_related``
      - ``N + 2``: the list, one attribute lookup shared by all entities, and
        one query per entity for its values
    * - With ``prefetch_related``
      - 3, however long the list is

The shared attribute lookup applies only to models that keep the default
:meth:`~eav.registry.EavConfig.get_attributes`.

Saving
------

Saving an entity writes only the values you assigned, and loads the
attributes and values it needs once. For many entities, use the
:doc:`bulk methods <bulk>`.
