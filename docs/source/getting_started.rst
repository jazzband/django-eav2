Getting Started
===============

Installation
------------

You can install **django-eav2** from PyPI, git or directly from source:

From PyPI
^^^^^^^^^
::

    pip install django-eav2

With pip via git
^^^^^^^^^^^^^^^^
::

    pip install git+https://github.com/lvm/django-eav2@master

From source
^^^^^^^^^^^
::

    git clone git@github.com:lvm/django-eav2.git
    cd django-eav2
    python setup.py install

To uninstall::

    python setup.py install --record files.txt
    rm $(cat files.txt)

Configuration
-------------

After you've installed the package, you have to add it to your Django apps::

    INSTALLED_APPS = [
        # ...

        'eav',

        # ...
    ]
