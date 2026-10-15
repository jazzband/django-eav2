Registering models
==================

An entity is any Django model you register with Django EAV 2. This page
covers how to register a model, what registration changes, and how to limit
which attributes a model can have.

Register with a function or a decorator
---------------------------------------

Call :func:`~eav.register` once for each model:

.. code-block:: python

    import eav

    eav.register(Part)

The decorator does the same thing. Call it with parentheses:

.. code-block:: python

    from eav.decorators import register_eav

    @register_eav()
    class Supplier(models.Model):
        ...

Both forms accept a config class, described in the next section. The
decorator takes it as the ``config_cls`` argument:

.. code-block:: python

    @register_eav(config_cls=SupplierEavConfig)
    class Supplier(models.Model):
        ...

Registering the same model twice is harmless, because the second call does
nothing. That includes a second call with a different config class, which is
ignored too. To change the config, call :func:`~eav.unregister` first.

What registration changes
-------------------------

Registration makes five changes to your model class:

1. It attaches an :class:`~eav.managers.EntityManager`, which replaces the
   default ``objects`` manager. The manager adds the ``eav__`` lookups and the
   bulk methods. See `Configure a model`_ to attach it under another name.
2. It connects the model's ``post_init`` signal to
   :meth:`~eav.registry.Registry.attach_eav_attr`, which gives every
   instance an :class:`~eav.models.Entity` helper. The helper reads, stores,
   and validates attribute values, and is available as ``instance.eav``.
3. It connects the ``pre_save`` and ``post_save`` signals to
   :meth:`~eav.models.Entity.pre_save_handler` and
   :meth:`~eav.models.Entity.post_save_handler`, which validate and store the
   values when the instance is saved.
4. It adds a generic relation from the model to its
   :class:`~eav.models.Value` objects, named ``eav_values`` by default.
5. It stores the config class on the model as ``_eav_config_cls``.

With ``manager_only = True`` in the config, only changes 1 and 5 happen: the
model gets the manager, but no helper, signals, or generic relation.

For example, the relation gives you every stored value of one entity:

.. code-block:: python

    patient.eav_values.all()
    # <QuerySet [Fever: "True" (Ada), Temperature: "37.7" (Ada)]>

Configure a model
-----------------

Subclass :class:`~eav.registry.EavConfig`, override the options you want to
change, and pass the class when you register. For example, to attach the EAV
manager as ``eav_objects`` instead of replacing ``objects``:

.. code-block:: python

    from eav.registry import EavConfig

    class SupplierEavConfig(EavConfig):
        manager_attr = "eav_objects"

    eav.register(Supplier, SupplierEavConfig)

    Supplier.eav_objects.filter(eav__city="London")

The manager that was already called ``objects`` keeps its name, and only
``eav_objects`` understands ``eav__`` lookups. Every other example in this
guide uses ``objects``, so use ``eav_objects`` in its place.

:doc:`configuration` lists every option.

.. _limit-attributes:

Limit the attributes of a model
-------------------------------

By default, every :class:`~eav.models.Attribute` applies to every registered
model. Override the
:meth:`~eav.registry.EavConfig.get_attributes` class method to narrow that
down. It receives the instance, which is ``None`` when no single instance is
involved, and returns a queryset of attributes:

.. code-block:: python

    from eav.models import Attribute

    class PatientEavConfig(EavConfig):
        @classmethod
        def get_attributes(cls, instance=None):
            return Attribute.objects.filter(slug__startswith="a")

    eav.register(Patient, PatientEavConfig)

Assigning a value to an attribute the model cannot have raises
:class:`~eav.exceptions.IllegalAssignmentException` when you save:

.. code-block:: python

    patient.eav.beard = True
    patient.save()  # raises IllegalAssignmentException

.. note::

    A model that overrides ``get_attributes`` looks up its attributes for each
    instance. Models that keep the default share one lookup across a queryset,
    which is faster. See :doc:`performance`.
