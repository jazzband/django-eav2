[![Jazzband](https://jazzband.co/static/img/jazzband.svg)](https://jazzband.co/)

This is a [Jazzband](https://jazzband.co/) project. By contributing you agree to abide by the [Contributor Code of Conduct](https://jazzband.co/about/conduct) and follow the [guidelines](https://jazzband.co/about/guidelines).

# Contributing
We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Dependencies

We use [uv](https://docs.astral.sh/uv/) to manage the dependencies
and [poethepoet](https://poethepoet.natn.io) as the task runner.

To install everything you need for development:

```bash
uv sync
```

To activate your `virtualenv` run `source .venv/bin/activate`,
or prefix commands with `uv run`.


## Tests

We use `pytest` and `ruff` for quality control.

```bash
uv run poe unit      # tests
uv run poe lint      # ruff check and format check
uv run poe format    # apply ruff fixes and formatting
uv run poe package   # lockfile check, build, dependency check
uv run poe test      # all of the above
```

To build the docs: `uv sync --group docs && uv run poe docs`.

## We develop with Github
We use github to host code, to track issues and feature requests, as well as accept pull requests.

### We use [Github Flow](https://guides.github.com/introduction/flow/index.html), so all code changes from community happen through pull requests
Pull requests are the best way to propose changes to the codebase (we use [Github Flow](https://guides.github.com/introduction/flow/index.html)). We actively welcome your pull requests:

1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Describe the pull request using [this](https://github.com/jazzband/django-eav2/blob/master/PULL_REQUEST_TEMPLATE.md) template.

### Any contributions you make will be under the GNU Lesser General Public License v3.0
In short, when you submit code changes, your submissions are understood to be under the same [LGPLv3](https://choosealicense.com/licenses/lgpl-3.0/) that covers the project. Feel free to contact the maintainers if that's a concern.

### Report bugs using Github's [issues](https://github.com/jazzband/django-eav2/issues)
We use GitHub issues to track public bugs. Report a bug by opening a new issue. Use [this](https://github.com/jazzband/django-eav2/blob/master/.github/ISSUE_TEMPLATE/bug_report.md) template to describe your reports.


### Use a consistent coding style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting, [wemake-python-styleguide](https://github.com/wemake-services/wemake-python-styleguide) (WPS) for stricter structural rules, and [Google-style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) reStructuredText for doc-strings.

`setup.cfg` lists the few WPS exceptions that are permanent, each with its reason. New code must pass without adding entries; if a rule is wrong for your case, propose changing the rule rather than adding contortions to the code.

Name variables for what they hold instead of the bare word `value`: an `eav.models.Value` row is `eav_value`, what a caller assigns is `raw_value`, and what a validator receives is `candidate`. The public API (`Value`, `Value.value`, `entity.eav.<slug>`) does not change.

### Write clear documentation

The docs are reStructuredText in `docs/source`, built with Sphinx. When you add or change a page:

- Organize pages around what a reader wants to do, and keep one topic per page.
- Write headings in sentence case, with no punctuation at the end. Stay within three levels.
- Use short sentences, the active voice, and plain words. Refer to a reader or a user as "they", never "he" or "she".
- Use a table when list items have several parallel parts, such as a name, a default, and a purpose.
- Link to a page instead of repeating it, and say what the link leads to.
- Skip filler words such as "simply" and "just", and write wording that includes every reader.
- Make code samples complete enough to run, with names that explain themselves.
- Build with `uv run poe docs`, which fails on any warning.

<hr>

<br>
<br>
This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md).
