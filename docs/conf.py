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
sys.path.insert(0, os.path.abspath('../'))

# -- Project information -----------------------------------------------------

project = "pooltool"
copyright = "2024, Evan Kiefl"
author = "Evan Kiefl"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx_copybutton",
    "autoapi.extension",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "custom_directives",
    "custom_extensions",
]


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# NOTE: Don't use this for excluding python files, use `autoapi_ignore` below
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Global options ----------------------------------------------------------

# Don't mess with double-dash used in CLI options
smartquotes_action = "qe"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_logo = '../pooltool/logo/logo_small.png'

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

# -- copybutton options
copybutton_exclude = '.linenos, .gp, .go'

# -- myst options
myst_enable_extensions = ["colon_fence"]

# -- autoapi configuration ---------------------------------------------------

#autodoc_typehints = "signature"  # autoapi respects this
autodoc_typehints = "both"  # autoapi respects this
autodoc_typehints_description_target = "documented_params"  # autoapi respects this
autodoc_class_signature = "mixed"
autoclass_content = "class"

autoapi_type = "python"
autoapi_dirs = ["../pooltool"]
autoapi_template_dir = "_templates/autoapi"
autoapi_options = [
    "members",
    #"undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
autoapi_keep_files = True

autoapi_ignore = [
    '*/test_*.py',
    "*/render.py",
    "*/ai/*",
    "*/ani/*",
    "*/user_config.py"
]


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


def skip_member(app, what, name, obj, skip, options):
    # Put debugger here to explore
    return skip


def setup(sphinx):
    sphinx.connect("autoapi-skip-member", skip_member)


autoapi_prepare_jinja_env = prepare_jinja_env

# Custom role for labels used in auto_summary() tables.
rst_prolog = """
.. role:: summarylabel
"""

# Related custom CSS
html_css_files = [
    "css/label.css",
    "css/sig.css",
]


#def autoapi_skip_members(app, what, name, obj, skip, options):
#    # skip submodules
#    if what == "module":
#        skip = True
#    elif what == "data":
#        if obj.name in ["EASING_FUNCTIONS", "ParamType"]:
#            skip = True
#    elif what == "function":
#        if obj.name in ["working_directory"]:
#            skip = True
#    elif "vsketch.SketchClass" in name:
#        if obj.name in [
#            "vsk",
#            "param_set",
#            "execute_draw",
#            "ensure_finalized",
#            "execute",
#            "get_params",
#            "set_param_set",
#        ]:
#            skip = True
#    elif "vsketch.Param" in name:
#        if obj.name in ["set_value", "set_value_with_validation"]:
#            skip = True
#    return skip
#
#
#def setup(app):
#    app.connect("autoapi-skip-member", autoapi_skip_members)
