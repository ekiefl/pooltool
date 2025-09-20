from sphinx.util.docutils import SphinxDirective

class PlaceholderDirective(SphinxDirective):
    pass


def setup(app):
    app.add_directive("placeholder", PlaceholderDirective)
