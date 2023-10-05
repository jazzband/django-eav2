[![Build Status](https://github.com/jazzband/django-eav2/actions/workflows/test.yml/badge.svg)](https://github.com/jazzband/django-eav2/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/jazzband/django-eav2/branch/master/graph/badge.svg?token=BJk3zS22BS)](https://codecov.io/gh/jazzband/django-eav2)
[![Python Version](https://img.shields.io/pypi/pyversions/django-eav2.svg)](https://pypi.org/project/django-eav2/)
[![Django Version](https://img.shields.io/pypi/djversions/django-eav2.svg?color=green)](https://pypi.org/project/django-eav2/)
[![Jazzband](https://jazzband.co/static/img/badge.svg)](https://jazzband.co/)

## Django EAV 2 - Entity-Attribute-Value storage for Django

Django EAV 2 is a fork of django-eav. You can find documentation <a href="https://django-eav2.rtfd.io">here</a> for more information.

## What is new here ?

With this version of django eav, you can use an IntegerField or a UUIDField as the primary key for your eav models.
You can also use the natural key for serialization instead of the primary key.


## Installation

Install with pip

```bash
pip install django-eav2
```

## Configuration

Add `eav` to `INSTALLED_APPS` in your settings.

```python
INSTALLED_APPS = [
    ...
    'eav',
]
```

Add `django.db.models.UUIDField` or `django.db.models.BigAutoField` as value of `PRIMARY_KEY_FIELD` in your settings

``` python
PRIMARY_KEY_FIELD = "django.db.models.UUIDField" # as exemple
```
### Note: Primary key mandatory modification field

If the primary key of eav models are to be modified (UUIDField -> BigAutoField, BigAutoField -> UUIDField) in the middle of the project when the migrations are already done, you have to change the value of `PRIMARY_KEY_FIELD` in your settings.

##### Step 1
 Change the value of `PRIMARY_KEY_FIELD` into `django.db.models.CharField` in your settings.

 ```python
 PRIMARY_KEY_FIELD = "django.db.models.CharField"
 ```

 Run the migrations

 ```bash
 python manage.py makemigrations
 python manage.py migrate
 ```

##### Step 2
 Change the value of `PRIMARY_KEY_FIELD` into the desired value (`django.db.models.BigAutoField` or `django.db.models.UUIDField`) in your settings.

 ```python
 PRIMARY_KEY_FIELD = "django.db.models.BigAutoField" # as exemple
 ```

  Run again the migrations.

```bash
 python manage.py makemigrations
 python manage.py migrate
 ```

### Note: Django 2.2 Users

Since `models.JSONField()` isn't supported in Django 2.2, we use [django-jsonfield-backport](https://github.com/laymonage/django-jsonfield-backport) to provide [JSONField](https://docs.djangoproject.com/en/dev/releases/3.1/#jsonfield-for-all-supported-database-backends) functionality.

This requires adding `django_jsonfield_backport` to your `INSTALLED_APPS` as well.

```python
INSTALLED_APPS = [
    ...
    'eav',
    'django_jsonfield_backport',
]
```

## Getting started

**Step 1.** Register a model:

```python
import eav
eav.register(Supplier)
```

or with decorators:

```python
from eav.decorators import register_eav

@register_eav
class Supplier(models.Model):
    ...
```

**Step 2.** Create an attribute:

```python
Attribute.objects.create(name='City', datatype=Attribute.TYPE_TEXT)
```

**Step 3.** That’s it! You’re ready to go:

```python
supplier.eav.city = 'London'
supplier.save()

Supplier.objects.filter(eav__city='London')
# = <EavQuerySet [<Supplier: Supplier object (1)>]>
```

**For futher information? Check out the django eav2 <a href="https://django-eav2.readthedocs.io/en/latest/#documentation">documentation</a>.**

---
