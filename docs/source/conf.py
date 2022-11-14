# Sphinx documentation generator configuration.
#
# More information on the configuration options is available at:
#     https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from typing import Dict

import django
from django.conf import settings
from sphinx.ext.autodoc import between

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../../'))

# Pass settings into configure.
settings.configure(
    INSTALLED_APPS=[
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'eav',
    ],
    SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY', 'this-is-not-s3cur3'),
)

# Call django.setup to load installed apps and other stuff.
django.setup()

# -- Project information -----------------------------------------------------

project = 'Django EAV 2'
copyright = '2018, Iwo Herka and team at MAKIMO'
author = '-'

# The short X.Y version
version = ''
# The full version, including alpha/beta/rc tags
release = '0.10.0'


def setup(app):
    """Use the configuration file itself as an extension."""
    app.connect(
        'autodoc-process-docstring',
        between(
            '^.*IGNORE.*$',
            exclude=True,
        ),
    )
    return app


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx_rtd_theme',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

language = 'en'

exclude_patterns = ['build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------


html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']

html_sidebars = {
    'index': ['sidebarintro.html', 'localtoc.html'],
    '**': [
        'sidebarintro.html',
        'localtoc.html',
        'relations.html',
        'searchbox.html',
    ],
}

htmlhelp_basename = 'DjangoEAV2doc'


# -- Options for LaTeX output ------------------------------------------------

latex_elements: Dict[str, str] = {}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'DjangoEAV2.tex', 'Django EAV 2 Documentation', '-', 'manual'),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        master_doc,
        'djangoeav2',
        'Django EAV 2 Documentation',
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
        'DjangoEAV2',
        'Django EAV 2 Documentation',
        author,
        'DjangoEAV2',
        'One line description of project.',
        'Miscellaneous',
    ),
]

# -- Extension configuration -------------------------------------------------

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'https://docs.python.org/': None}

# -- Autodoc configuration ---------------------------------------------------

add_module_names = False
