Getting Started
===============

Installation
------------
::

    pip install django-eav2

Configuration
-------------

After you've installed the package, you have to add it to your Django apps
::

    INSTALLED_APPS = [
        ...
        'eav',
    ]

Note: Django 2.2 Users
^^^^^^^^^^^^^^^^^^^^^^

Since ``models.JSONField()`` isn't supported in Django 2.2, we use `django-jsonfield-backport <https://github.com/laymonage/django-jsonfield-backport>`_
 to provide `JSONField <https://docs.djangoproject.com/en/dev/releases/3.1/#jsonfield-for-all-supported-database-backends>`_
 functionality.

This requires adding ``django_jsonfield_backport`` to your INSTALLED_APPS as well.


::

    INSTALLED_APPS = [
        ...
        'eav',
        'django_jsonfield_backport',
    ]
