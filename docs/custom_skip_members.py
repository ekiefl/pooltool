# def autoapi_skip_members(app, what, name, obj, skip, options):
#    print(what, name, skip)
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
# def setup(app):
#    app.connect("autoapi-skip-member", autoapi_skip_members)
