# Version History

## 1.0.0 (2021-10-21)

## Breaking Changes

- Drops support for `django1.x`
- Drops support for `django3.0`
- Moves `JSONField()` datatype to `django-jsonfield-backport` for Django2.2 instances

## Features

- Adds support for `django3.2`
- Adds support for `python3.9`
- Adds support for `defaults` keyword on `get_or_create()`

## Misc

- Revamps all tooling, including moving to `poetry`, `pytest`, and `black`
- Adds Github Actions and Dependabot

**Full Changelog**: https://github.com/jazzband/django-eav2/compare/0.14.0...1.0.0

## 0.14.0 (2021-04-23)

## Misc

- This release will be the last to support this range of Django versions: 1.11, 2.0, 2.1, 2.2, 3.0. SInce all of their extended support was ended by Django Project.
- From the next release only will be supported 2.2 LTS, 3.1, and 3.2 LTS (eventually 4.x)

**Full Changelog**: https://github.com/jazzband/django-eav2/compare/0.13.0...0.14.0

(Anything before 0.14.0 was not recorded.)
