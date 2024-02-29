import re

import attr
from sphinx.application import Sphinx


def extract_qualified_name(obj):
    repr_str = repr(obj)
    class_or_instance_method_pattern = r"<bound method ([\w\.]+)\.([\w]+) of"
    static_or_func_pattern = r"<function ([\w\.]*\w+)"
    lambda_pattern = r"<function <lambda>"

    class_or_instance_match = re.search(class_or_instance_method_pattern, repr_str)
    static_or_func_match = re.search(static_or_func_pattern, repr_str)
    lambda_match = re.search(lambda_pattern, repr_str)

    if class_or_instance_match:
        return f"{class_or_instance_match.group(1)}.{class_or_instance_match.group(2)}"
    elif static_or_func_match:
        return static_or_func_match.group(1)
    elif lambda_match:
        return "UNKNOWN"
    else:
        return "UNKNOWN"


def process_signature(app, what, name, obj, options, signature, return_annotation):
    # Check if the object is a class or a method of an attrs class
    if attr.has(obj) or (hasattr(obj, "__objclass__") and attr.has(obj.__objclass__)):
        cls = obj if attr.has(obj) else obj.__objclass__
        attrs_fields = attr.fields_dict(cls)

        new_signature = signature
        for field_name, attr_obj in attrs_fields.items():
            if isinstance(attr_obj.default, attr.Factory):
                # Extract full name from the factory's __repr__
                factory_full_name = extract_qualified_name(attr_obj.default.factory)
                replacement_str = f"{factory_full_name}"

                # Define a regex pattern to match the parameter, its type, and the default value
                pattern = re.compile(rf"({field_name}: [^=]+ = )_Nothing.NOTHING")
                # Replace with the new default value representation
                new_signature = pattern.sub(rf"\1{replacement_str}", new_signature)

        return new_signature, return_annotation


def setup(app: Sphinx):
    app.connect("autodoc-process-signature", process_signature)
