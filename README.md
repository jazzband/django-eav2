[![Build Status](https://travis-ci.org/makimo/django-eav2.svg?branch=master)](https://travis-ci.org/makimo/django-eav2)
[![Coverage Status](https://coveralls.io/repos/github/makimo/django-eav2/badge.svg?branch=master)](https://coveralls.io/github/makimo/django-eav2?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/159540d899bd41bb860f0ce996427e1f)](https://www.codacy.com/app/IwoHerka/django-eav2?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=makimo/django-eav2&amp;utm_campaign=Badge_Grade)
[![Maintainability](https://api.codeclimate.com/v1/badges/b90eacf7a90db4b58f13/maintainability)](https://codeclimate.com/github/makimo/django-eav2/maintainability)
![Python Version](https://img.shields.io/badge/Python-2.7,%203.5,%203.6,%203.7dev-blue.svg)
![Django Version](https://img.shields.io/badge/Django-1.11,%202.0,%20tip-green.svg)

### Django EAV 2 - Entity-Attribute-Value storage for Django

#### Introduction

Django EAV 2 is a fork of django-eav (which itself was derived from eav-django).
This project aims to:

- add Python 3 support
- add Django 1.11 and 2.0 support
- modernize and clean-up the codebase
- drop Django <1.11 dependencies
- remove dependency on Sites framework
- fix unresolved issues
- update documentation (Sphinx + ReadTheDocs)
- create exhaustive (and automated) tests
- add new features

(For now) our progress can be tracked through issues. Feel free
to join the discussion.

### Installing from git

```
pip install git+https://github.com/makimo/django-eav2@master
```

### Installing from source

```
git clone git@github.com:makimo/django-eav2.git
cd django-eav2
python setup.py install
```
To uninstall:
```
python setup.py install --record files.txt
rm $(cat files.txt)
```
