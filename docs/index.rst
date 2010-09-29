.. django-eav documentation master file, created by
   sphinx-quickstart on Fri Sep 24 10:48:33 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

##########
django-eav
##########


Introduction
============
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
============
You can install django-eav directly from guthub::

    pip install -e git+git://github.com/mvpdev/django-eav.git#egg=django-eav

After installing, add ``eav`` to your ``INSTALLED_APPS`` in your
project's ``settings.py`` file.

Usage
=====
In order to attach EAV attributes to a model, you first need to register it
(just like you may register your models with django.contrib.admin).

Registration
------------
Registering a model with eav does a few things:

* Adds the eav :class:`eav.managers.EntityManager` to your class.  By default,
  it will replace the default ``objects`` manager of the model, but you can
  choose to have the eav manager named something else if you don't want it to
  replace ``objects`` (see :ref:`advancedregistration`).
* Connects the model's ``post_init`` signal to
  :meth:`~eav.registry.Registry.attach_eav_attr`. This function will attach
  the eav :class:`eav.models.Entity` helper class to every instance of your
  model when it is instatiated.  By default, it will be attached to your models
  as an attribute named ``eav``, which will allow you to access it through
  ``my_model_instance.eav``, but you can choose to name it something else if you
  want (again see :ref:`advancedregistration`).
* Connect's the model's ``pre_save`` signal to
  :meth:`eav.models.Entity.pre_save_handler`.
* Connect's the model's ``post_save`` signal to
  :meth:`eav.models.Entity.post_save_handler`.
* Adds a generic relation helper to the class.
* Sets an attribute called ``_eav_config_cls`` on the model class to either
  the default :class:`eav.registry.EavConfig` config class, or to the config
  class you provided during registration.

If that all sounds too complicated, don't worry, you really don't need to think
about it.  Just thought you should know.

Simple Registration
^^^^^^^^^^^^^^^^^^^
To register any model with EAV, you simply need to add the registration line
somewhere that will be executed when django starts::

    import eav
    eav.register(MyModel)

Generally, the most appropriate place for this would be in your ``models.py``
immediately after your model definition.

.. _advancedregistration:

Advanced Registration
^^^^^^^^^^^^^^^^^^^^^
Advanced registration is only required if:

* You don't want eav to replace your model's default ``objects`` manager.
* You want to name the :class:`~eav.models.Entity` helper attribute something
  other than ``eav``
* You don't want all eav :class:`~eav.models.Attribute` objects to
  be able to be set for all of your registered models. In other words, you
  have different types of entities, each with different attributes.

Advanced registration is simple, and is performed the exact same way
you override the django.contrib.admin registration defaults.

You just need to define your own config class that subclasses
:class:`~eav.registry.EavConfig` and override the default class attributes
and method.

There are five :class:`~eav.registry.EavConfig` class attributes you can
override:

================================= ================================== ==========================================================================
Class Attribute                   Default                            Description
================================= ================================== ==========================================================================
``manager_attr``                  ``'objects'``                      The name of the eav manager
``manager_only``                  ``False``                          *boolean* Whether to *only* replace the manager, and do nothing else
``eav_attr``                      ``'eav'``                          The attribute name of the entity helper
``generic_relation_attr``         ``'eav_values'``                   The attribute name of the generic relation helper
``generic_relation_related_name`` The model's ``__class__.__name__`` The related name of the related name of the generic relation to your model
================================= ================================== ==========================================================================

An example of just choosing a different name for the manager (and thus leaving
``objects`` intact)::

    class MyEavConfigClass(EavConfig):
        manager_attr = 'eav_objects'

    eav.register(MyModel, MyEavConfigClass)

Additionally, :class:`~eav.registry.EavConfig` defines a classmethod called
``get_attributes`` that, by default will return ``Attribute.objects.all()``
This method is used to determine which :class:`~eav.models.Attribute` can be
applied to the entity model you are registering. If you want to limit which
attributes can be applied to your entity, you would need to override it.

For example::

    class MyEavConfigClass(EavConfig):
        @classmethod
        def get_attributes(cls):
            return Attribute.objects.filter(type='person')

    eav.register(MyModel, MyEavConfigClass)


Using Attributes
================
Once you've registered your model(s), you can begin to use them with EAV
attributes. Let's assume your model is called ``Person`` and it has one
normal django ``CharField`` called name, but you want to be able to dynamically
store other data about each Person.

First, let's create some attributes::

    >>> Attribute.objects.create(name='Weight', datatype=Attribute.TYPE_FLOAT)
    >>> Attribute.objects.create(name='Height', datatype=Attribute.TYPE_INT)
    >>> Attribute.objects.create(name='Is pregant?', datatype=Attribute.TYPE_BOOLEAN)

Now let's create a patient, and set some of these attributes::

    >>> p = Patient.objects.create(name='Bob')
    >>> p.eav.height = 46
    >>> p.eav.weight = 42.2
    >>> p.eav.is_pregnant = False
    >>> p.save()
    >>> bob = Patient.objects.get(name='Bob')
    >>> bob.eav.height
    46
    >>> bob.eav.weight
    42.2
    >>> bob.is_pregnant
    False

Additionally, assuming we're using the eav manager, we can also do::

    >>> p = Patient.objects.create(name='Jen', eav__height=32, eav__pregnant=True)


Filtering
=========

eav attributes are filterable, using the same __ notation as django foreign
keys::

    Patient.objects.filter(eav__weight=42.2)
    Patient.objects.filter(eav__weight__gt=42)
    Patient.objects.filter(name='Bob', eav__weight__gt=42)
    Patient.objects.exclude(eav__is_pregnant=False)

You can even use Q objects, however there are some known issues
(see :ref:`qobjectissue`) with Q object filters::

    Patient.objects.filter(Q(name='Bob') | Q(eav__is_pregnant=False))

What about if you have a foreign key to a model that uses eav, but you want
to filter from a model that doesn't use eav?  For example, let's say you have
a ``Patient`` model that **doesn't** use eav, but it has a foreign key to
``Encounter`` that **does** use eav. You can even filter through eav across
this relationship, but you need to use the eav manager for ``Patient``.

Just register ``Patient`` with eav, but set ``manager_only = True``
see (see :ref:`advancedregistration`).  Then you can do::

    Patient.objects.filter(encounter__eav__weight=2)


Admin Integration
=================

You can even have your eav attributes show up just like normal fields in your
models admin pages.  Just register using the eav admin class::

    from django.contrib import admin
    from eav.forms import BaseDynamicEntityForm
    from eav.admin import BaseEntityAdmin 

    class PatientAdminForm(BaseDynamicEntityForm):
        model = Patient

    class PatientAdmin(BaseEntityAdmin):
        form = PatientAdminForm

    admin.site.register(Patient, PatientAdmin)


Known Issues
============

.. _qobjectissue:

Q Object Filters
----------------
Due to an unexplained Q object / generic relation issue, exclude filters with
EAV Q objects, or EAV Q objects ANDed together may produce inaccurate results.

Additional Resources
====================

.. toctree::
   :maxdepth: 2

   docstrings

