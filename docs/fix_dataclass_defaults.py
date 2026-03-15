import dataclasses

from sphinx.application import Sphinx


def process_signature(app, what, name, obj, options, signature, return_annotation):
    if what != "class":
        return None

    if not dataclasses.is_dataclass(obj):
        return None

    if signature is None or "<factory>" not in signature:
        return None

    factory_fields = [
        f
        for f in dataclasses.fields(obj)
        if f.default_factory is not dataclasses.MISSING and f.init
    ]

    for f in factory_fields:
        factory_name = getattr(f.default_factory, "__name__", repr(f.default_factory))
        signature = signature.replace("<factory>", f"{factory_name}()", 1)

    return (signature, return_annotation)


def setup(app: Sphinx):
    app.connect("autodoc-process-signature", process_signature)
