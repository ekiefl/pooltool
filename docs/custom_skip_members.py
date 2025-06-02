from include_exclude import skip_dict, keep_dict


def autoapi_skip_members(app, what, name, obj, skip, options):
    if name in skip_dict.get(what, []):
        skip = True

    if name in keep_dict.get(what, []):
        skip = False

    return skip


def setup(app):
    app.connect("autoapi-skip-member", autoapi_skip_members)
