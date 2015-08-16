django-eav
==========


Introduction
------------

django-eav provides an Entity-Attribute-Value storage model for django apps.

For a decent explanation of what an Entity-Attribute-Value storage model is,
check `Wikipedia
<http://en.wikipedia.org/wiki/Entity-attribute-value_model>`_.

.. note::
   This software was inspired / derived from the excellent `eav-django
   <http://pypi.python.org/pypi/eav-django/1.0.2>`_ written by Andrey
   Mikhaylenko.
   
   There are a few notable differences between this implementation and the
   eav-django implementation.
   
   * This one is called django-eav, whereas the other is called eav-django.
   * This app allows you to to 'attach' EAV attributes to any existing django
     model (even from third-party apps) without making any changes to the those
     models' code.
   * This app has slightly more robust (but still not perfect) filtering.


Installation
------------

From Github
~~~~~~~~~~~
You can install django-eav directly from guthub::

    pip install -e git+git://github.com/mvpdev/django-eav.git#egg=django-eav

Prerequisites
-------------

Django Sites Framework
~~~~~~~~~~~~~~~~~~~~~~
As of Django 1.7, the `Sites framework <https://docs.djangoproject.com/en/1.8/ref/contrib/sites/#enabling-the-sites-framework>`_ is not enabled by default; Django-EAV requires this framework.
To enable the sites framework, follow these steps:

Add ``django.contrib.sites`` to your INSTALLED_APPS setting. Be sure to add sites to the installed apps list BEFORE eav!

Define a ``SITE_ID`` setting::

    SITE_ID = 1

Run ``migrate``


Usage
-----

Edit settings.py
~~~~~~~~~~~~~~~~
Add ``eav`` to your ``INSTALLED_APPS`` in your project's ``settings.py`` file. Be sure to add eav to the installed apps list AFTER the sites framework!

Register your model(s)
~~~~~~~~~~~~~~~~~~~~~~
Before you can attach eav attributes to your model, you must register your
model with eav::

    >>> import eav
    >>> eav.register(MyModel)

Generally you would do this in your ``models.py`` immediate after your model
declarations. Alternatively, you can use the registration decorator provided::

    from eav.decorators import register_eav
    @register_eav()
    class MyModel(models.Model):
        ...

Create some attributes
~~~~~~~~~~~~~~~~~~~~~~
::

    >>> from eav.models import Attribute
    >>> Attribute.objects.create(name='Weight', datatype=Attribute.TYPE_FLOAT)
    >>> Attribute.objects.create(name='Color', datatype=Attribute.TYPE_TEXT)


Assign eav values
~~~~~~~~~~~~~~~~~
::

    >>> m = MyModel()
    >>> m.eav.weight = 15.4
    >>> m.eav.color = 'blue'
    >>> m.save()
    >>> m = MyModel.objects.get(pk=m.pk)
    >>> m.eav.weight
    15.4
    >>> m.eav.color
    blue

    >>> p = MyModel.objects.create(eav__weight = 12, eav__color='red')

Filter on eav values
~~~~~~~~~~~~~~~~~~~~
::

    >>> MyModel.objects.filter(eav__weight=15.4)

    >>> MyModel.objects.exclude(name='bob', eav__weight=15.4, eav__color='red')


Documentation and Examples
--------------------------

`<http://mvpdev.github.com/django-eav>`_
