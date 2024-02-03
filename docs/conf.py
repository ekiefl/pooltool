# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
sys.path.insert(0, os.path.abspath('../pooltool'))


# -- Project information -----------------------------------------------------

project = 'pooltool'
copyright = '2024, Evan Kiefl'
author = 'Evan Kiefl'


# -- General configuration ---------------------------------------------------

def contains(seq, item):
    return item in seq

def prepare_jinja_env(jinja_env) -> None:
    jinja_env.tests["contains"] = contains

autoapi_prepare_jinja_env = prepare_jinja_env

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
# Add any Sphinx extension module names here, as strings

extensions = [
    #"sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "autoapi.extension",
]

autoapi_dirs = ['../pooltool/']
autoapi_type = "python"
autoapi_template_dir = "_templates/autoapi"
autoapi_keep_files = True
autodoc_typehints = "signature"

autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True


autodoc_default_options = {
    'undoc-members': False,
    'exclude-members': '__weakref__'
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    '**/test_*.py',
    '**/test_*/**',
]

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_logo = '../pooltool/logo/logo_small.png'

# E.g. Ball instead of pooltool.objects.ball.datatypes.Ball
python_use_unqualified_type_names = False

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = [
    "custom.css",
]

