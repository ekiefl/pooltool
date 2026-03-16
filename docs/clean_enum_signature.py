import enum

from sphinx.application import Sphinx


def process_signature(app, what, name, obj, options, signature, return_annotation):
    if what != "class":
        return None

    if not (isinstance(obj, type) and issubclass(obj, enum.Enum)):
        return None

    return ("", return_annotation)


def setup(app: Sphinx):
    app.connect("autodoc-process-signature", process_signature)
