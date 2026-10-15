# Sphinx documentation generator configuration.
#
# More information on the configuration options is available at:
#     https://www.sphinx-doc.org/en/master/usage/configuration.html
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

import django
from django.conf import settings
from sphinx.ext.autodoc import between

# For discovery of Python modules
sys.path.insert(0, str(Path().cwd()))

# For finding the django_settings.py file
sys.path.insert(0, str(Path("../../").resolve()))


# Pass settings into configure.
settings.configure(
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "eav",
    ],
    SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY", "this-is-not-s3cur3"),
    EAV2_PRIMARY_KEY_FIELD="django.db.models.BigAutoField",
)

# Call django.setup to load installed apps and other stuff.
django.setup()

# -- Project information -----------------------------------------------------

project = "Django EAV 2"
copyright = "2018, Iwo Herka and team at MAKIMO"  # noqa: A001
author = "-"

# The version comes from the package metadata, so it cannot go stale.
_pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
release = tomllib.loads(_pyproject.read_text())["project"]["version"]
version = release


def setup(app):
    """Use the configuration file itself as an extension."""
    app.connect(
        "autodoc-process-docstring",
        between(
            "^.*IGNORE.*$",
            exclude=True,
        ),
    )
    return app


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]

source_suffix = ".rst"

master_doc = "index"

language = "en"

exclude_patterns = ["build"]


# -- Options for HTML output -------------------------------------------------


html_theme = "shibuya"

html_static_path = ["_static"]

html_theme_options = {
    "github_url": "https://github.com/jazzband/django-eav2",
    "readthedocs_url": "https://django-eav2.readthedocs.io",
}

html_context = {
    "source_type": "github",
    "source_user": "jazzband",
    "source_repo": "django-eav2",
    "source_version": "master",
    "source_docs_path": "/docs/source/",
}

htmlhelp_basename = "DjangoEAV2doc"


# -- Options for LaTeX output ------------------------------------------------

latex_elements: dict[str, str] = {}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, "DjangoEAV2.tex", "Django EAV 2 Documentation", "-", "manual"),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        master_doc,
        "djangoeav2",
        "Django EAV 2 Documentation",
        [author],
        1,
    ),
]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "DjangoEAV2",
        "Django EAV 2 Documentation",
        author,
        "DjangoEAV2",
        "One line description of project.",
        "Miscellaneous",
    ),
]

# -- Extension configuration -------------------------------------------------

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# -- Autodoc configuration ---------------------------------------------------

add_module_names = False
