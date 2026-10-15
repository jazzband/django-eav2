Bulk operations
===============

``bulk_create()`` and ``bulk_update()`` on a registered model's manager store
attribute values as well as fields. Each batch costs one query for the entities,
plus one for each datatype you set, instead of one or more queries per entity.

Create many entities
--------------------

Assign values on each instance, as you would before a single ``save()``, then
pass the list to ``bulk_create()``:

.. code-block:: python

    patients = []
    for name, age in rows:
        patient = Patient(name=name)
        patient.eav.age = age
        patient.eav.city = "London"
        patients.append(patient)

    Patient.objects.bulk_create(patients)

``bulk_create()`` first validates every instance: required attributes, value
types, enum choices, and unknown attributes. If any instance is invalid, it
raises before it writes anything. It then writes the instances and their
values in one transaction, in batches, so no single statement grows without
limit.

Update many entities
--------------------

List attributes as ``eav__<slug>`` next to ordinary fields:

.. code-block:: python

    for patient in patients:
        patient.name = patient.name.title()
        patient.eav.age += 1

    Patient.objects.bulk_update(patients, ["name", "eav__age"])

Only attributes with a value assigned on the instance are written. Assigning
``None`` or an empty string deletes the stored value.

Choose a batch size
-------------------

Both methods write ``batch_size`` entities at a time, and send at most that
many rows in one ``INSERT``. The default is 1000. Set ``bulk_batch_size`` in
the model's config to change it, or pass ``batch_size`` for a single call,
which takes precedence:

.. code-block:: python

    class PatientEavConfig(EavConfig):
        bulk_batch_size = 2000

    eav.register(Patient, PatientEavConfig)

    Patient.objects.bulk_create(patients, batch_size=500)

Larger batches mean fewer queries but bigger statements. On a local database,
anything from 500 to a few thousand performs about the same. The main gain
above 1000 is fewer round trips to a networked database. Keep these limits in
mind:

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Database
      - Limit
    * - PostgreSQL
      - 65,535 bind parameters per statement, when the driver binds on the
        server
    * - MySQL
      - Limited by ``max_allowed_packet``
    * - SQLite
      - The variable limit. The batch size is lowered automatically.

Limitations
-----------

* **No signals.** As with Django's own bulk methods, no signals are sent, so
  ``Value`` signal handlers and history tracking do not run for values
  written this way. ``save()`` on a single entity is unchanged.
* **Primary keys are needed.** New entities need keys to link their values to.
  UUID keys always work. Integer keys work on PostgreSQL, SQLite, and MariaDB.
  MySQL does not return auto-increment keys, so use UUID keys there.
* **Conflict options.** ``ignore_conflicts`` and ``update_conflicts`` cannot
  be combined with attribute values.
