from docutils import nodes
from sphinx.util.nodes import make_refnode


FALLBACK_ROLES = ("class", "data", "attribute", "obj")

INTERNAL_MODULE_ALIASES = {
    "pathlib._local.Path": "pathlib.Path",
    "pathlib._local.PurePath": "pathlib.PurePath",
}


def _resolve_type_aliases(app, env, node, contnode):
    """Resolve missing Python domain references.

    Handles three cases:
    1. Internal CPython module paths (e.g. pathlib._local.Path -> pathlib.Path).
    2. Intersphinx role mismatches (e.g. NDArray registered as :data: not :class:).
    3. Re-exported objects (e.g. a.b.Foo documented as a.Foo).
    """
    if node.get("refdomain") != "py":
        return None

    target = node["reftarget"]
    target = INTERNAL_MODULE_ALIASES.get(target, target)

    if node.get("reftype") == "class":
        named_inv = getattr(env, "intersphinx_named_inventory", {})
        for _proj_name, proj_inv in named_inv.items():
            for role in FALLBACK_ROLES:
                key = f"py:{role}"
                if key in proj_inv and target in proj_inv[key]:
                    _proj, _version, uri, _dispname = proj_inv[key][target]
                    short_name = target.rsplit(".", 1)[-1]
                    newnode = nodes.reference(
                        short_name, short_name, internal=False, refuri=uri
                    )
                    return newnode

    parts = target.split(".")
    if len(parts) >= 3:
        py_domain = env.get_domain("py")
        short_name = parts[-1]
        for i in range(len(parts) - 2, 0, -1):
            candidate = ".".join(parts[:i] + [parts[-1]])
            entry = py_domain.objects.get(candidate)
            if entry is not None:
                return make_refnode(
                    app.builder,
                    node.get("refdoc", ""),
                    entry.docname,
                    entry.node_id,
                    nodes.Text(short_name),
                    short_name,
                )

    return None


def _fix_ellipsis_display(app, doctree, docname):
    """Replace hyperlinked 'Ellipsis' with plain '...' text."""
    for ref in doctree.findall(nodes.reference):
        if ref.astext() == "Ellipsis" and "constants.html#Ellipsis" in ref.get("refuri", ""):
            ref.replace_self(nodes.Text("..."))


def setup(app):
    app.connect("missing-reference", _resolve_type_aliases)
    app.connect("doctree-resolved", _fix_ellipsis_display)
