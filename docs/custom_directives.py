from docutils import nodes
from sphinx.util.docutils import SphinxDirective

class CachedPropertyDirective(SphinxDirective):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True

    def run(self):
        targetid = "cached-property-%d" % self.env.new_serialno('cached-property')
        targetnode = nodes.target('', '', ids=[targetid])

        text = f"""This is a cached property, and should be accessed as an attribute, not as a method call."""
        para = nodes.paragraph(text, text)

        return [targetnode, para]


def setup(app):
    app.add_directive("cached_property_note", CachedPropertyDirective)
