Getting started
===============

This page takes you from installation to your first stored and queried
attribute. It takes about five minutes.

Requirements
------------

Django EAV 2 supports Python 3.10 and later, and Django 5.2, 6.0, and 6.1.

Install the package
-------------------

.. code-block:: bash

    pip install django-eav2

If you use `uv <https://docs.astral.sh/uv/>`_, run ``uv add django-eav2``
instead.

Add the app and run the migrations
----------------------------------

Add ``eav`` to ``INSTALLED_APPS``, then create its tables:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        "eav",
    ]

.. code-block:: bash

    python manage.py migrate

.. note::

    The package's tables use ``BigAutoField`` primary keys by default. To use
    UUIDs, set ``EAV2_PRIMARY_KEY_FIELD`` before the first ``migrate``. See
    :ref:`primary-key-setting`.

Register a model
----------------

Registering a model gives it the ``eav`` helper and the ``eav__`` lookups.
Do it once per model, for example at the bottom of ``models.py``:

.. code-block:: python

    import eav

    eav.register(Supplier)

You can also use the decorator. Note the parentheses:

.. code-block:: python

    from eav.decorators import register_eav

    @register_eav()
    class Supplier(models.Model):
        name = models.CharField(max_length=100)

Create an attribute
-------------------

An attribute has a name and a datatype. The slug, which is how you refer to
the attribute in code, is generated from the name:

.. code-block:: python

    from eav.models import Attribute

    Attribute.objects.create(name="City", datatype=Attribute.TYPE_TEXT)

You can also create attributes in the Django admin.

Store and query values
----------------------

Assign values through the ``eav`` helper and save the instance as usual:

.. code-block:: python

    supplier = Supplier.objects.create(name="Acme")
    supplier.eav.city = "London"
    supplier.save()

    supplier.eav.city  # "London"

Filter with the ``eav__`` prefix, which works like a Django field lookup:

.. code-block:: python

    Supplier.objects.filter(eav__city="London")
    Supplier.objects.filter(eav__city__startswith="Lon", name="Acme")

Next steps
----------

* :doc:`concepts` explains the model behind the library and its trade-offs.
* :doc:`attributes` covers every datatype.
* :doc:`querying` shows the lookups you can use.
* :doc:`performance` explains the value cache and how to avoid extra queries.
