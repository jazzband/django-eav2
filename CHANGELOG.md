# Version History

We follow [Semantic Versions](https://semver.org/) starting at the `0.14.0` release.

## 1.8.0 (2025-02-24)

## What's Changed

- Add database constraints to Value model for data integrity by @Dresdn in https://github.com/jazzband/django-eav2/pull/706
- Fix for issue #648: Ensure choices are valid (value, label) tuples by @altimore in https://github.com/jazzband/django-eav2/pull/707

## 1.7.1 (2024-09-01)

## What's Changed
* Restore backward compatibility for Attribute creation with invalid slugs by @Dresdn in https://github.com/jazzband/django-eav2/pull/639

## 1.7.0 (2024-09-01)

### What's Changed

- Enhance slug validation for Python identifier compliance
- Migrate to ruff
- Drop support for Django 3.2
- Add support for Django 5.1

## 1.6.1 (2024-06-23)

### What's Changed

- Ensure eav.register() Maintains Manager Order by @Dresdn in https://github.com/jazzband/django-eav2/pull/595
- Update downstream dependencies by @Dresdn in https://github.com/jazzband/django-eav2/pull/597

## 1.6.0 (2024-03-14)

### What's Changed

- Corrects `BaseEntityAdmin` integration into Django Admin site
- Split model modules by @iacobfred in https://github.com/jazzband/django-eav2/pull/467
- Add Django 5.0 and Python 3.12 to the testing by @cclauss in https://github.com/jazzband/django-eav2/pull/487
- Fix typos with codespell by @cclauss in https://github.com/jazzband/django-eav2/pull/489
- Enhance BaseEntityAdmin by @Dresdn in https://github.com/jazzband/django-eav2/pull/541
- Remove support for Django < 3.2 and Python < 3.8 by @Dresdn in https://github.com/jazzband/django-eav2/pull/542

## 1.5.0 (2023-11-08)

### Bug Fixes

- Fixes querying with multiple eav kwargs [#395](https://github.com/jazzband/django-eav2/issues/395)

### Features

- Support for many type of primary key (UUIDField, BigAutoField)
- Support for natural key use for some models for serialization (EnumValue, EnumGroup, Attribute, Value)
- Add support for Django 4.2
- Add support for Python 3.11

## 1.4.0 (2023-07-07)

### Features

- Support Bahasa Indonesia Translations
- Support Django 4.2

## 1.3.1 (2023-02-22)

### Bug Fixes

- Generate missing migrations [#331](https://github.com/jazzband/django-eav2/issues/331)

## 1.3.0 (2023-02-10)

### Features

- Add support for Django 4.1

### Bug Fixes

- Fixes missing `Add another` button for inlines in `BaseEntityAdmin`
- Fixes saving of Attribute date types rendering using `BaseDynamicEntityForm` [#261](https://github.com/jazzband/django-eav2/issues/261)

### Misc

- Drops support for Django 2.2 and Python 3.7

## 1.2.3 (2022-08-15)

### Bug Fixes

- Don't mark doc8 as a dependency [#235](https://github.com/jazzband/django-eav2/issues/235)
- Make Read the Docs dependencies all optional

## 1.2.2 (2022-08-13)

### Bug Fixes

- Fixes AttributeError when using CSVFormField [#187](https://github.com/jazzband/django-eav2/issues/187)
- Fixes slug generation for Attribute.name fields longer than 50 characters [#223](https://github.com/jazzband/django-eav2/issues/223)
- Migrates Attribute.slug to django.db.models.SlugField() [#223](https://github.com/jazzband/django-eav2/issues/223)

## 1.2.1 (2022-02-08)

### Bug Fixes

- Fixes FieldError when filtering on foreign keys [#163](https://github.com/jazzband/django-eav2/issues/163)

## 1.2.0 (2021-12-18)

### Features

- Adds 64-bit support for `Value.value_int`
- Adds Django 4.0 and Python 3.10 support

### Misc

- Drops support for Django 3.1 and Python 3.6

## 1.1.0 (2021-11-07)

### Features

- Adds support for entity models with UUId as a primary key #38

### Bug Fixes

- Fixes `ValueError` for models without local managers #41
- Fixes `str()` and `repr()` for `EnumGroup` and `EnumValue` objects #91

### Misc

- Bumps min python version to `3.6.2`

**Full Changelog**: <https://github.com/jazzband/django-eav2/compare/1.0.0...1.1.0>

## 1.0.0 (2021-10-21)

### Breaking Changes

- Drops support for `django1.x`
- Drops support for `django3.0`
- Moves `JSONField()` datatype to `django-jsonfield-backport` for Django2.2 instances

### Features

- Adds support for `django3.2`
- Adds support for `python3.9`
- Adds support for `defaults` keyword on `get_or_create()`

### #Misc

- Revamps all tooling, including moving to `poetry`, `pytest`, and `black`
- Adds Github Actions and Dependabot

**Full Changelog**: <https://github.com/jazzband/django-eav2/compare/0.14.0...1.0.0>

## 0.14.0 (2021-04-23)

### Misc

- This release will be the last to support this range of Django versions: 1.11, 2.0, 2.1, 2.2, 3.0. SInce all of their extended support was ended by Django Project.
- From the next release only will be supported 2.2 LTS, 3.1, and 3.2 LTS (eventually 4.x)

**Full Changelog**: <https://github.com/jazzband/django-eav2/compare/0.13.0...0.14.0>

(Anything before 0.14.0 was not recorded.)
