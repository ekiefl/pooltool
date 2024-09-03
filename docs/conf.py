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

sys.path.insert(0, os.path.abspath("./"))
sys.path.insert(0, os.path.abspath("../"))

# -- Project information -----------------------------------------------------

project = "pooltool"
copyright = "2024, Evan Kiefl"
author = "Evan Kiefl"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "nbsphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx_copybutton",
    "sphinx_tabs.tabs",
    "autoapi.extension",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "custom_directives",
    "custom_extensions",
    "custom_skip_members",
]


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# NOTE: Don't use this for excluding python files, use `autoapi_ignore` below
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints", "**.ipynb", "**README.md"]

# -- Global options ----------------------------------------------------------

# Don't mess with double-dash used in CLI options
smartquotes_action = "qe"

# -- Notebook rendering -------------------------------------------------

# Something to consider: https://dokk.org/documentation/nbsphinx/0.9.3/prolog-and-epilog/
nbsphinx_epilog = """"""
nbsphinx_prolog = """"""

nbsphinx_custom_formats = {
    ".pct.py": ["jupytext.reads", {"fmt": "py:percent"}],
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_logo = "../pooltool/logo/logo_small.png"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# -- Napoleon options
napoleon_include_init_with_doc = False
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True

napolean_use_param = True  # Each parameter is its own :param: directive
napolean_use_rtype = False  # This does't work :(
napolean_attr_annotations = True

# -- Intersphinx options
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "attrs": ("https://www.attrs.org/en/stable/", None),
    "numba": ("https://numba.readthedocs.io/en/stable/", None),
}

# -- sphinx-tabs options
sphinx_tabs_disable_tab_closing = True

# -- copybutton options
copybutton_exclude = ".linenos, .gp, .go"

# -- myst options
myst_enable_extensions = ["colon_fence"]

# -- autoapi configuration ---------------------------------------------------

# autodoc_typehints = "signature"  # autoapi respects this
autodoc_typehints = "both"  # autoapi respects this
autodoc_typehints_description_target = "documented_params"  # autoapi respects this
autodoc_class_signature = "mixed"
autoclass_content = "class"

autoapi_type = "python"
autoapi_dirs = ["../pooltool"]
autoapi_template_dir = "_templates/autoapi"
autoapi_options = [
    "members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
autoapi_keep_files = True

autoapi_ignore = [
    "*/test_*.py",
    "*/render.py",
    "*/ai/*",
    "*/user_config.py",
]
# Everything in ani/ except animate.py
autoapi_ignore.extend(
    [
        "*/ani/camera/*",
        "*/ani/fonts/*",
        "*/ani/image/*",
        "*/ani/modes/*",
        "*/ani/__init__.py",
        "*/ani/action.py",
        "*/ani/collision.py",
        "*/ani/environment.py",
        "*/ani/globals.py",
        "*/ani/hud.py",
        "*/ani/menu.py",
        "*/ani/mouse.py",
        "*/ani/tasks.py",
        "*/ani/utils.py",
        "*/error.py",
        "*/terminal.py",
    ]
)


# -- custom auto_summary() macro ---------------------------------------------


def contains(seq, item):
    """Jinja2 custom test to check existence in a container.

    Example of use:
    {% set class_methods = methods|selectattr("properties", "contains", "classmethod") %}

    Related doc: https://jinja.palletsprojects.com/en/3.1.x/api/#custom-tests
    """
    return item in seq


def prepare_jinja_env(jinja_env) -> None:
    """Add `contains` custom test to Jinja environment."""
    jinja_env.tests["contains"] = contains


autoapi_prepare_jinja_env = prepare_jinja_env

# Custom role for labels used in auto_summary() tables.
rst_prolog = """
.. role:: summarylabel
"""

# Related custom CSS
html_css_files = [
    "css/label.css",
]
