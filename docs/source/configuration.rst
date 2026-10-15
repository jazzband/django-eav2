Configuration
=============

Django EAV 2 has one Django setting, and one config class for each registered
model.

.. _primary-key-setting:

The ``EAV2_PRIMARY_KEY_FIELD`` setting
--------------------------------------

The package's own tables use ``BigAutoField`` primary keys by default. To use
UUIDs, set this in your settings **before you run** ``migrate`` **for the
first time**:

.. code-block:: python

    EAV2_PRIMARY_KEY_FIELD = "django.db.models.UUIDField"

The only supported values are ``django.db.models.BigAutoField`` and
``django.db.models.UUIDField``. Any other value raises
``ImproperlyConfigured``. Both the models and the migrations read the setting,
so a new project gets the key type it asked for with no extra steps.

The setting only affects the tables the package creates. Your own models can
use any integer or UUID primary key.

.. warning::

    Changing the setting for tables that already exist is not supported, and
    no migration converts existing keys. If you need to switch, migrate your
    data yourself.

The ``EavConfig`` options
-------------------------

Pass a subclass of :class:`~eav.registry.EavConfig` as the second argument to
:func:`~eav.register`, or as ``config_cls`` to the decorator, to change these
options for one model:

.. list-table::
    :header-rows: 1
    :widths: 28 14 58

    * - Option
      - Default
      - Purpose
    * - ``manager_attr``
      - ``"objects"``
      - The name of the manager that
        :class:`~eav.managers.EntityManager` takes over.
    * - ``manager_only``
      - ``False``
      - When ``True``, only the manager is attached. Signals and the generic
        relation are not set up.
    * - ``eav_attr``
      - ``"eav"``
      - The name of the :class:`~eav.models.Entity` helper on each instance.
    * - ``generic_relation_attr``
      - ``"eav_values"``
      - The name of the generic relation from an entity to its
        :class:`~eav.models.Value` objects.
    * - ``generic_relation_related_name``
      - Model class name
      - The name used to query values from an entity, for example
        ``Value.objects.filter(Patient__name="Ada")``.
    * - ``bulk_batch_size``
      - ``1000``
      - How many entities ``bulk_create`` and ``bulk_update`` write at a time.
        See :doc:`bulk`.
    * - ``cache_values``
      - ``True``
      - Whether ``instance.eav.<slug>`` loads values once and reuses them. Set
        it to ``False`` for models whose values are written outside
        ``instance.eav`` and ``save()``. See :doc:`performance`.

.. code-block:: python

    class SupplierEavConfig(EavConfig):
        manager_attr = "eav_objects"
        bulk_batch_size = 500

    eav.register(Supplier, SupplierEavConfig)

Choose the attributes of a model
--------------------------------

Override the :meth:`~eav.registry.EavConfig.get_attributes` class method to
limit which attributes apply to a model. See :ref:`limit-attributes`.
