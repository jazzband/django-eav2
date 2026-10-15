Django EAV 2
============

Django EAV 2 stores extra, typed attributes for your Django models without
changing their tables. Define an attribute once, then read, write, and filter
it on any registered model as if it were a field.

.. code-block:: python

    import eav
    from django.db import models
    from eav.models import Attribute

    class Supplier(models.Model):
        name = models.CharField(max_length=100)

    eav.register(Supplier)
    Attribute.objects.create(name="City", datatype=Attribute.TYPE_TEXT)

    supplier = Supplier.objects.create(name="Acme", eav__city="London")
    supplier.eav.city  # "London"

    Supplier.objects.filter(eav__city="London")

The attributes live in their own tables, so an administrator can add or
change them at runtime, in the Django admin or in code, without a migration.

New to the library? Start with :doc:`getting_started`. To decide whether the
entity-attribute-value pattern fits your problem, read :doc:`concepts`.

.. toctree::
    :caption: Guide
    :maxdepth: 1

    getting_started
    concepts
    registering
    attributes
    querying
    bulk
    performance
    admin

.. toctree::
    :caption: Reference
    :maxdepth: 1

    configuration
    api

.. toctree::
    :caption: Project
    :maxdepth: 1

    GitHub <https://github.com/jazzband/django-eav2>
    Changelog <https://github.com/jazzband/django-eav2/blob/master/CHANGELOG.md>
    Issues <https://github.com/jazzband/django-eav2/issues>
