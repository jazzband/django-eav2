Concepts
========

How it works
------------

An entity-attribute-value (EAV) model splits a record into three parts:

.. list-table::
    :header-rows: 1
    :widths: 18 32 50

    * - Part
      - In Django EAV 2
      - Example
    * - Entity
      - Any registered Django model instance
      - ``Patient(name="Mike")``
    * - Attribute
      - A row of :class:`~eav.models.Attribute`, with a name and a datatype
      - ``Attribute(slug="height", datatype="float")``
    * - Value
      - A row of :class:`~eav.models.Value`, linking one entity to one
        attribute
      - ``Value(value_float=1.8, attribute=height)``

Because attributes are rows, not columns, you can add and change them while
the application runs. An attribute that has stored values cannot be deleted
until its values are, and its datatype cannot change. Each value is stored in a column that matches the
attribute's datatype, so values are typed and can be filtered. Numbers, dates, and enum choices
are also indexed.

When to use it
--------------

EAV fits when the set of properties is open-ended and each record uses only a
few of them. Typical cases are:

* Attributes that administrators or end users define, such as custom fields
  in a SaaS product.
* Product catalogs where each category has different properties.
* Sparse data, where a wide table would be mostly ``NULL``.
* Configuration or metadata that changes more often than your release cycle.

When to avoid it
----------------

EAV trades query speed and simplicity for flexibility. Avoid it when:

* Reads must be fast. Each attribute you filter on adds a lookup on the values
  table, which is slower than filtering on a plain column.
* The properties are known up front and stable. Real columns are simpler, can
  be constrained by the database, and are easier to maintain.
* You report across many attributes at once. Aggregations over EAV data are
  harder to write and slower to run.

Use EAV for the part of your schema that needs the flexibility and keep the
rest in ordinary fields.

Alternatives
------------

On PostgreSQL, MySQL, and SQLite, a ``JSONField`` can hold flexible data with
less machinery. It gives up a shared attribute catalog, per-attribute
validation, and the admin integration, and some JSON lookups depend on the
database backend. Consider it first when you do not need those.

Further reading
---------------

* `Entity-attribute-value model <https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model>`_
  (Wikipedia)
* `What is so bad about EAV, anyway? <https://sqlblog.org/2009/11/19/what-is-so-bad-about-eav-anyway>`_
* `Exploring performance issues for a clinical database organized using an
  entity-attribute-value representation <https://doi.org/10.1136/jamia.2000.0070475>`_
