
[![Build Status](https://travis-ci.org/makimo/django-eav2.svg?branch=master)](https://travis-ci.org/makimo/django-eav2)
[![Coverage Status](https://coveralls.io/repos/github/makimo/django-eav2/badge.svg?branch=master)](https://coveralls.io/github/makimo/django-eav2?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/159540d899bd41bb860f0ce996427e1f)](https://www.codacy.com/app/IwoHerka/django-eav2?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=makimo/django-eav2&amp;utm_campaign=Badge_Grade)
[![Maintainability](https://api.codeclimate.com/v1/badges/b90eacf7a90db4b58f13/maintainability)](https://codeclimate.com/github/makimo/django-eav2/maintainability)
![Python Version](https://img.shields.io/badge/Python-2.7,%203.5,%203.6,%203.7dev-blue.svg)
![Django Version](https://img.shields.io/badge/Django-1.11,%202.0,%20tip-green.svg)

## Django EAV 2 - Entity-Attribute-Value storage for Django

Django EAV 2 is a fork of django-eav (which itself was derived from eav-django). 
You can find documentation <a href="https://django-eav-2.readthedocs.io/en/improvement-docs/">here</a>.

## Installation
You can install **django-eav2** from three sources:
```bash
# From PyPI via pip
pip install django-eav2

# From source via pip
pip install git+https://github.com/makimo/django-eav2@master

# From source via setuptools
git clone git@github.com:makimo/django-eav2.git
cd django-eav2
python setup.py install

# To uninstall:
python setup.py install --record files.txt
rm $(cat files.txt)
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

### What next? Check out <a href="https://django-eav-2.readthedocs.io/en/improvement-docs/">documentation</a>.
