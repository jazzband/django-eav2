Performance and caching
=======================

This page explains when Django EAV 2 queries the database and how to keep the
number of queries low.

How reads are cached
--------------------

The first time you read ``instance.eav.<slug>``, the library loads the
entity's attributes and all of its values, and keeps them on the instance.
Later reads need no queries. Reading three attributes, for example, takes two
queries in total, not two per attribute.

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

Upgrading from 1.x
------------------

Version 1.x queried the database on every read of ``instance.eav.<slug>``.
Version 2.0 loads the values once and reuses them, so a read can return an old
value when something other than the instance changed the data:

* ``Value.objects.bulk_create()``, ``QuerySet.update()`` and
  ``QuerySet.delete()``, a raw query, or another process.
* A test suite or a block of code that disconnects the ``pre_save`` and
  ``post_save`` receivers. Django EAV 2 clears the cache and writes the values
  from those receivers, so with them disconnected ``save()`` does neither.
  Call ``instance.eav.clear_cache()`` yourself.

If your code relied on always-fresh reads, call ``instance.eav.clear_cache()``
after such writes, or set ``cache_values = False`` on the models you write
that way. See `Reading stale values`_.

Listing many entities
---------------------

Prefetch the values when you read attributes across a list. Prefetch
``eav_values__attribute``, because ``eav_values`` alone still queries once per
row. If you changed ``generic_relation_attr``, use that name in place of
``eav_values``:

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
      - 3, or 4 when some entity has no value for the attribute you read,
        however long the list is

The shared attribute lookup applies only to models that keep the default
:meth:`~eav.registry.EavConfig.get_attributes`.

Saving
------

Saving an entity writes only the values you assigned, and loads the
attributes and values it needs once. For many entities, use the
:doc:`bulk methods <bulk>`.
