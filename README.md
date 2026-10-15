[![Build Status](https://github.com/jazzband/django-eav2/actions/workflows/test.yml/badge.svg)](https://github.com/jazzband/django-eav2/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/jazzband/django-eav2/branch/master/graph/badge.svg?token=BJk3zS22BS)](https://codecov.io/gh/jazzband/django-eav2)
[![Python Version](https://img.shields.io/pypi/pyversions/django-eav2.svg)](https://pypi.org/project/django-eav2/)
[![Django Version](https://img.shields.io/pypi/djversions/django-eav2.svg?color=green)](https://pypi.org/project/django-eav2/)
[![Jazzband](https://jazzband.co/static/img/badge.svg)](https://jazzband.co/)

## Django EAV 2

Django EAV 2 stores extra, typed attributes for your Django models without
changing their tables. Define an attribute once, then read, write, and filter it
on any registered model as if it were a field. Administrators can add and
change attributes at runtime, in the Django admin or in code, without a
migration.

It is a fork of django-eav, which was itself derived from eav-django.

**Read the documentation at <https://django-eav2.readthedocs.io>.**

## Install

```bash
pip install django-eav2
```

Add `eav` to `INSTALLED_APPS`, then run `python manage.py migrate`:

```python
INSTALLED_APPS = [
    # ...
    "eav",
]
```

The package's tables use `BigAutoField` primary keys. To use UUIDs, set
`EAV2_PRIMARY_KEY_FIELD = "django.db.models.UUIDField"` **before the first
`migrate`**. See the [configuration docs](https://django-eav2.readthedocs.io/en/latest/configuration.html).

## Quick start

Register a model, create an attribute, then store and query values:

```python
import eav
from eav.models import Attribute

eav.register(Supplier)

Attribute.objects.create(name="City", datatype=Attribute.TYPE_TEXT)

supplier = Supplier.objects.create(name="Acme", eav__city="London")
supplier.eav.city  # "London"

Supplier.objects.filter(eav__city="London")
```

## Is EAV right for you?

EAV trades query speed and simplicity for flexibility. It suits open-ended,
sparse or user-defined properties, and is a poor fit for stable, known columns
or performance-critical reporting. The
[concepts page](https://django-eav2.readthedocs.io/en/latest/concepts.html)
explains the model, when to use it, when to avoid it, and the alternatives.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The project is part of
[Jazzband](https://jazzband.co/), which has a
[code of conduct](https://jazzband.co/about/conduct).
