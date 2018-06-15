.. .. image:: _static/logo.png
..     :align: center

Django EAV 2
============

Django EAV 2 is an entity-attribute-value storage for modern Django.
Getting started is very easy.

Registering models looks as follows:

.. code-block:: python

    import eav
    eav.register(Supplier)

or with decorators:

.. code-block:: python

    from eav.decorators import register_eav

    @register_eav
    class Supplier(models.Model):
        ...

Create an attribute with:

.. code-block:: python

    Attribute.objects.create(name='City', datatype=Attribute.TYPE_TEXT)

and you're ready to go:

.. code-block:: python

    supplier.eav.city = 'London'
    supplier.save()

    Supplier.objects.filter(eav__city='London')
    # = <EavQuerySet [<Supplier: Supplier object (1)>]>


Documentation
-------------

.. toctree::
   :maxdepth: 2


API Reference
-------------

If you are looking for information on a specific function, class, or
method, this part of the documentation is for you.

.. toctree::
   :maxdepth: 2

   api

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
