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

We use [poetry](https://github.com/sdispater/poetry) to manage the dependencies.

To install them you would need to run `install` command:

```bash
poetry install
```

To activate your `virtualenv` run `poetry shell`.


## Tests

We use `pytest` and `flake8` for quality control.

To run all tests:

```bash
pytest
```

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

We use [Black](https://github.com/psf/black) and (working towards) [wemake-python-styleguide](https://github.com/wemake-services/wemake-python-styleguide) for code and [Google-style](http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) reStructuredText for doc-strings.

<hr>

<br>
<br>
This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md).
