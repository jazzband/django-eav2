# Version History

We follow [Semantic Versions](https://semver.org/) starting at the `0.14.0` release.

## Unreleased

### Breaking Changes

- `EAV2_PRIMARY_KEY_FIELD` accepts only `django.db.models.BigAutoField` (the default) and `django.db.models.UUIDField`. `django.db.models.CharField`, `django.db.models.AutoField` and any other value now raise `ImproperlyConfigured` instead of being ignored. A `CharField` key never worked on its own, because nothing generates the ids; it only existed as the middle step of a conversion described in the README.
- Migrations `0001` and `0010` use the configured key type, so a new project with `UUIDField` gets UUID keys from its first `migrate`; this fixes `cannot cast type bigint to uuid` on PostgreSQL (#455). Existing databases are unaffected. The README's two-step conversion, which generated migration files inside the installed package, is gone: converting the keys of existing tables is not supported.
- `order_by("eav__<enum attribute>")` now sorts by the text of the choice, so it does not depend on how the database orders keys. It used to sort by the choice's id.

### Deprecations

- The `json`, `csv`, and `object` attribute datatypes are deprecated and django-eav2 3.0 removes them, along with their value columns. Saving an attribute of one of these types, or writing a value to one (including `bulk_create()` and `bulk_update()`), emits `eav.exceptions.RemovedInEav3Warning`, a `FutureWarning` that points at your own code. Use a `JSONField`, a `ForeignKey`, a `ManyToManyField`, or a related model on your own model instead, and move existing data out of EAV before 3.0. If you have a use case that those do not cover, open an issue.

### Performance

- `instance.eav.<slug>` loads an entity's attributes and values once and reuses them, so reading three attributes takes 2 queries instead of 6. The values are held in the instance's `prefetch_related` cache, so `refresh_from_db()` and `save()` clear them; use `instance.eav.clear_cache()` after changing values elsewhere.
- Saving an entity loads its attributes and values once and writes only assigned values: creating an entity with three attributes takes 6 queries instead of 39, and saving one changed attribute takes 4 instead of 11.
- `prefetch_related("eav_values__attribute")` is now used when reading attributes, and entities from one queryset (including `.iterator()`) share a single attribute lookup. Reading one attribute across 10 prefetched entities takes 3 queries instead of 23.
- `EavConfig.cache_values = False` turns the value cache off for a model, so every read queries the database. Use it, or `instance.eav.clear_cache()`, when values are written outside `instance.eav` and `save()`, such as with `Value.objects.bulk_create`: cached reads do not see those writes.
- New `Attribute.store_value`, `Value.save_checked`, `Entity.clear_cache` and `EavConfig.shares_attributes`; `Attribute.save_value` keeps its behaviour.

- Migration `0013` adds indexes on `(attribute, value_int)`, `(attribute, value_float)`, `(attribute, value_date)` and `(attribute, value_enum)`, so filters such as `eav__age__gt=5` and `eav__score=500` read the matching rows instead of every value of the attribute. On a table of 500,000 values an equality filter took 0.3 ms instead of 6.5 ms and a range filter 7 ms instead of 13 ms. Text values are not indexed.

### Features

- `bulk_create()` and `bulk_update()` on EAV managers store EAV values in about one query per 1000 rows instead of one or more per entity: `Patient.objects.bulk_create(patients)` writes the values assigned with `patient.eav.<slug> = ...`, and `bulk_update(patients, ["name", "eav__age"])` updates them. Instances are validated first, written in chunks inside one transaction, and no signals are sent. Creating entities needs primary keys, so integer keys are not supported on MySQL.
- `EavConfig.bulk_batch_size` (1000 by default) sets how many entities `bulk_create()` and `bulk_update()` write at a time; the `batch_size` argument overrides it.
- `Attribute.enum_choices`, `Attribute.validate_assignment`, `Entity.assigned_values` and `Value.clean_own_fields`. Saving an enum attribute no longer queries the choices more than once.

### Bug Fixes

- `~Q()` on an attribute inside a larger `Q` removes whole entities, as `exclude()` does. It used to negate single value rows, so `filter(Q(eav__age__gt=30) & ~Q(eav__city="Nice"))` could return entities that live in Nice. Every condition on an attribute, in a `Q` or as a keyword argument, is now an independent `EXISTS` subquery, which also stops OR conditions from returning an entity more than once.
- `eav__<slug>__isnull=True` finds the entities that have no value for the attribute. It used to find nothing.
- Lookups chained after an attribute slug, such as `eav__born__year__gt=2000` or `eav__extras__chills__iexact="yes"`, are applied. They used to be dropped, which returned no rows.
- `filter()` no longer changes the `Q` objects you pass to it, so you can reuse them, and a `Q` that contains an expression such as `Exists(...)` no longer fails.
- A lookup other than equality on an `object` attribute raises `FieldError`. It used to be ignored, which returned wrong rows.
- Unregistering a model removes its generic relation, and the matching reverse relation on `Value`. It used to leave the relation behind, and every `register()` after an `unregister()` added another copy of it to the model.
- `BaseEntityInline` works: it used to fail with `AttributeError` when the inline had no `form`, and with `FieldError` when it had a `BaseDynamicEntityForm`. The inline now defaults to `BaseDynamicEntityForm`, shows the attributes of its own model, saves them, and honors `fields`. An attribute named like a reverse relation of the inline's model no longer fails.
- Filtering on several EAV attributes in one `filter()` call works on UUID-keyed entities.
- The Indonesian translation is compiled and ships with the package; its `.mo` file was missing. A test now fails if any compiled catalog differs from its `.po` source.

- `validate_enum` and `validate_object` use Django's `_state.adding` to detect unsaved instances, because a model with a UUID default key always has a primary key, so an unsaved `EnumValue` was accepted and then failed with an integrity error.

- `Value.entity_id` and `Value.generic_value_id` are now `BigIntegerField`, so entities with primary keys above 2,147,483,647 can store values (migration `0014`). On PostgreSQL and MySQL this rewrites the `eav_value` table, which takes a lock for as long as the rewrite runs on a large table, so plan the upgrade accordingly.
- Assigning a plain `date` to a date attribute stores midnight in the default timezone, as before, but no longer emits Django's "naive datetime" `RuntimeWarning` when `USE_TZ` is on, and saving the same date again no longer rewrites the value.

- `order_by("eav__<slug>")` no longer fails on UUID-keyed entities or empty querysets, no longer mixes in values of other models that share a primary key, and now accepts `-eav__<slug>` for descending order. Ordering by an `object` attribute raises `NotSupportedError` (it was a `FieldError`). Ordering by a related field such as `order_by("example__name")` now sorts by that field; it used to sort by the foreign key column only.
- `validate_int` and `validate_float` raise `ValidationError` instead of `TypeError` for `None` and other non-numeric types.
- An empty CSV value is read back as `[]` instead of `['']`.
- `BaseEntityInline.get_fieldsets` no longer recurses infinitely, and honours `fieldsets`.
- `EAV2_PRIMARY_KEY_FIELD` defaults to `BigAutoField` when it is not set, instead of raising `AttributeError`.
- Unknown attribute slugs raise `Attribute.DoesNotExist` with the same message from `filter`, `exclude`, `get` and `order_by`.
- `Entity.get_values` names the related fields it loads, which removes a Django 6.1 deprecation warning.

### Internal

- The documentation is reorganized into topic pages, uses the Shibuya theme, and fixes examples that did not run: `@register_eav` needs parentheses, the decorator accepts `config_cls`, and CSV attributes filter with `__contains`.
- `eav/` is fully typed and passes mypy strict, pyright and wemake-python-styleguide with no baseline of ignores; the few permanent WPS exceptions in `setup.cfg` each give a reason. Parameters named `value` on internal helpers are now `candidate` or `raw_value` (`Attribute.validate_value`, `validate_assignment`, `store_value`, `save_value` and the validators); the public API is unchanged.
- Moved from Poetry to uv, hatchling and poethepoet.
- Docstrings are required in `eav/`, module layers are enforced with `import-linter`, and the docs are linted with `sphinx-lint`.
- Added `py.typed`, wemake-python-styleguide, mypy and pyright, Postgres and MySQL CI jobs, and Python 3.14 and Django 6.1 to the test matrix.

## 1.8.2 (2026-05-22)

## What's Changed

### Bug Fixes

- Fixed `TypeError: 'Q' object is not subscriptable` when combining EAV filters with negated Q objects by @Dresdn in https://github.com/jazzband/django-eav2/pull/846

### Compatibility

- Added Django 6.0 support
- Dropped support for EOL Django versions — minimum is now Django 5.2
- Dropped support for EOL Python versions — minimum is now Python 3.10

## 1.8.1 (2025-06-02)

## What's Changed

- Added support for Django 5.2
- Updated dependencies to their latest versions

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
