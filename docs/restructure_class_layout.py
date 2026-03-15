from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx


def _inline_attr_types(doctree):
    for desc_node in doctree.traverse(addnodes.desc):
        if desc_node.get("objtype") != "attribute":
            continue

        sigs = list(desc_node.traverse(addnodes.desc_signature))
        contents = list(desc_node.traverse(addnodes.desc_content))
        if not sigs or not contents:
            continue

        sig = sigs[0]
        content = contents[0]

        type_nodes = None
        type_field = None
        type_field_list = None

        for fl in content.traverse(nodes.field_list):
            for field in list(fl.traverse(nodes.field)):
                fn = field.traverse(nodes.field_name)
                if fn and fn[0].astext().strip() == "Type":
                    fb = field.traverse(nodes.field_body)
                    if fb:
                        paras = fb[0].traverse(nodes.paragraph)
                        if paras:
                            type_nodes = list(paras[0].children)
                    type_field = field
                    type_field_list = fl
                    break
            if type_nodes is not None:
                break

        if type_nodes is None:
            continue

        insert_idx = len(sig.children)
        for i, child in enumerate(sig.children):
            if isinstance(child, nodes.reference) and "headerlink" in child.get(
                "classes", []
            ):
                insert_idx = i
                break

        new_nodes = [
            addnodes.desc_sig_space("", " "),
            addnodes.desc_sig_punctuation("", ":"),
            addnodes.desc_sig_space("", " "),
        ]
        new_nodes.extend(_unwrap_emphasis([tn.deepcopy() for tn in type_nodes]))

        for j, nn in enumerate(new_nodes):
            sig.insert(insert_idx + j, nn)

        type_field.parent.remove(type_field)
        if not type_field_list.children:
            type_field_list.parent.remove(type_field_list)


def _restructure_class_sections(doctree):
    for desc_node in doctree.traverse(addnodes.desc):
        if desc_node.get("objtype") != "class":
            continue

        contents = list(desc_node.traverse(addnodes.desc_content))
        if not contents:
            continue
        content = contents[0]

        bases_para = None
        for child in content.children:
            if isinstance(child, nodes.paragraph) and child.astext().startswith("Bases:"):
                bases_para = child
                break

        base_link_nodes = []
        if bases_para is not None:
            base_link_nodes = [
                child.deepcopy()
                for child in bases_para.children
                if not (isinstance(child, nodes.Text) and child.astext().startswith("Bases:"))
            ]
            content.remove(bases_para)

        docstring_nodes = []
        for child in list(content.children):
            if isinstance(child, addnodes.desc) and child.get("objtype") == "attribute":
                break
            if isinstance(child, nodes.rubric):
                break
            docstring_nodes.append(child)

        for node in docstring_nodes:
            content.remove(node)

        has_attrs = any(
            isinstance(c, addnodes.desc) and c.get("objtype") == "attribute"
            for c in content.children
        )

        insert_items = []

        if docstring_nodes:
            insert_items.extend(docstring_nodes)

        if base_link_nodes:
            insert_items.append(nodes.rubric("", "Base Classes:"))
            new_para = nodes.paragraph(classes=["base-classes"])
            new_para.extend(base_link_nodes)
            insert_items.append(new_para)

        if has_attrs:
            insert_items.append(nodes.rubric("", "Attributes:"))

        for j, item in enumerate(insert_items):
            content.insert(j, item)


def _remove_members_from_toc(app, doctree, docname):
    remove_ids = set()
    for desc in doctree.traverse(addnodes.desc):
        if desc.get("objtype") in ("attribute", "method", "property"):
            for sig in desc.traverse(addnodes.desc_signature):
                remove_ids.update(sig.get("ids", []))

    if not remove_ids:
        return

    toc = app.env.tocs.get(docname)
    if toc is None:
        return

    to_remove = []
    for ref in toc.traverse(nodes.reference):
        anchorname = ref.attributes.get("anchorname", "")
        refid = anchorname.lstrip("#") or ref.attributes.get("refid", "")
        if refid in remove_ids:
            list_item = ref.parent.parent
            if isinstance(list_item, nodes.list_item):
                to_remove.append(list_item)

    for item in to_remove:
        if item.parent is not None:
            item.parent.remove(item)


def _restyle_param_fields(doctree):
    for field_list in doctree.traverse(nodes.field_list):
        for field in field_list.traverse(nodes.field):
            fn = field.traverse(nodes.field_name)
            if not fn:
                continue
            name = fn[0].astext().strip()

            fb = field.traverse(nodes.field_body)
            if not fb:
                continue
            body = fb[0]

            if name == "Parameters":
                _restyle_params_body(body)
            elif name == "Return type":
                _restyle_return_type(body)


def _restyle_params_body(body):
    has_bullet = any(isinstance(c, nodes.bullet_list) for c in body.children)
    if has_bullet:
        for bl in body.traverse(nodes.bullet_list):
            for item in bl.traverse(nodes.list_item):
                paras = [c for c in item.children if isinstance(c, nodes.paragraph)]
                if paras:
                    _restyle_single_param(paras[0], item)
    else:
        paras = [c for c in body.children if isinstance(c, nodes.paragraph)]
        if paras:
            _restyle_single_param(paras[0], body)


def _restyle_single_param(para, container):
    children = list(para.children)
    if not children:
        return

    first = children[0]
    if isinstance(first, (nodes.strong, addnodes.literal_strong)):
        param_name = first.astext()
    elif isinstance(first, nodes.reference) and first.traverse(nodes.strong):
        param_name = first.traverse(nodes.strong)[0].astext()
    else:
        return

    anchorlinks = []
    idx = 1
    while idx < len(children):
        child = children[idx]
        if isinstance(child, nodes.reference) and (
            set(child.get("classes", [])) & {"paramlink", "headerlink"}
        ):
            anchorlinks.append(child)
            idx += 1
        else:
            break

    type_nodes, desc_nodes = _split_type_and_desc(children[idx:])
    type_nodes = [n.deepcopy() for n in type_nodes]
    desc_nodes = [n.deepcopy() for n in desc_nodes]
    type_nodes = _unwrap_emphasis(type_nodes)

    line = [nodes.Text(param_name)]
    line.extend(anchorlinks)
    if type_nodes:
        line.append(nodes.Text(" : "))
        line.extend(type_nodes)

    new_para = nodes.paragraph("", classes=["param-sig"])
    for node in line:
        new_para.append(node)
    if para.get("ids"):
        new_para["ids"] = para["ids"]

    pos = list(container.children).index(para)
    container.remove(para)
    container.insert(pos, new_para)

    if desc_nodes:
        desc_para = nodes.paragraph("", classes=["param-desc"])
        for node in desc_nodes:
            desc_para.append(node)
        container.insert(pos + 1, desc_para)


def _split_type_and_desc(children):
    type_nodes = []
    desc_nodes = []
    phase = "looking"

    for child in children:
        if phase == "looking":
            if isinstance(child, nodes.Text):
                text = str(child)
                paren = text.find("(")
                if paren >= 0:
                    after_open = text[paren + 1 :]
                    close = after_open.find(")")
                    if close >= 0:
                        if after_open[:close]:
                            type_nodes.append(nodes.Text(after_open[:close]))
                        remaining = _strip_separator(after_open[close + 1 :])
                        if remaining:
                            desc_nodes.append(nodes.Text(remaining))
                            phase = "desc"
                        else:
                            phase = "after_close"
                    else:
                        if after_open:
                            type_nodes.append(nodes.Text(after_open))
                        phase = "type"
                else:
                    sep_after = _find_separator(text)
                    if sep_after is not None:
                        if sep_after:
                            desc_nodes.append(nodes.Text(sep_after))
                        phase = "desc"

        elif phase == "type":
            if isinstance(child, nodes.Text):
                text = str(child)
                close = text.find(")")
                if close >= 0:
                    if text[:close]:
                        type_nodes.append(nodes.Text(text[:close]))
                    remaining = _strip_separator(text[close + 1 :])
                    if remaining:
                        desc_nodes.append(nodes.Text(remaining))
                        phase = "desc"
                    else:
                        phase = "after_close"
                else:
                    type_nodes.append(child)
            else:
                type_nodes.append(child)

        elif phase == "after_close":
            if isinstance(child, nodes.Text):
                text = str(child)
                stripped = _strip_separator(text)
                if stripped != text:
                    if stripped:
                        desc_nodes.append(nodes.Text(stripped))
                    phase = "desc"
                else:
                    desc_nodes.append(child)
                    phase = "desc"
            else:
                desc_nodes.append(child)
                phase = "desc"

        elif phase == "desc":
            desc_nodes.append(child)

    return type_nodes, desc_nodes


def _strip_separator(text):
    for sep in [" \u2013 ", " -- "]:
        if text.startswith(sep):
            return text[len(sep) :]
    return text


def _find_separator(text):
    for sep in [" \u2013 ", " -- "]:
        idx = text.find(sep)
        if idx >= 0:
            return text[idx + len(sep) :]
    return None


def _unwrap_emphasis(node_list):
    _emphasis_types = (nodes.emphasis, addnodes.literal_emphasis)
    result = []
    for node in node_list:
        if isinstance(node, _emphasis_types):
            result.extend(node.children)
        elif isinstance(node, nodes.reference):
            new_children = []
            changed = False
            for child in node.children:
                if isinstance(child, _emphasis_types):
                    new_children.extend(child.children)
                    changed = True
                else:
                    new_children.append(child)
            if changed:
                node.children = new_children
                for child in node.children:
                    child.parent = node
            result.append(node)
        else:
            result.append(node)
    return result


def _restyle_return_type(body):
    body["classes"] = body.get("classes", []) + ["return-type"]
    _emphasis_types = (nodes.emphasis, addnodes.literal_emphasis)
    for emphasis in list(body.traverse(lambda n: isinstance(n, _emphasis_types))):
        parent = emphasis.parent
        idx = parent.children.index(emphasis)
        parent.remove(emphasis)
        for i, child in enumerate(emphasis.children):
            parent.insert(idx + i, child)


def process_doctree(app, doctree, docname):
    _inline_attr_types(doctree)
    _restructure_class_sections(doctree)
    _restyle_param_fields(doctree)
    _remove_members_from_toc(app, doctree, docname)


def setup(app: Sphinx):
    app.connect("doctree-resolved", process_doctree)
