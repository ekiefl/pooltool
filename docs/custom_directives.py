from docutils import nodes
from sphinx.util.docutils import SphinxDirective


class CachedPropertyDirective(SphinxDirective):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True

    def run(self):
        targetid = f"cached-property-{self.env.new_serialno('cached-property')}"
        targetnode = nodes.target("", "", ids=[targetid])

        # Create an admonition node to hold the content
        admonition_node = nodes.admonition()

        # Optional: Add a title to the admonition
        title_text = "Cached Property Note"
        admonition_node += nodes.title(title_text, title_text)

        # Text before the hyperlink
        pre_text = "This is a "
        post_text = ", and should be accessed as an attribute, not as a method call."

        # Creating the hyperlink
        uri = (
            "https://docs.python.org/3/library/functools.html#functools.cached_property"
        )
        link_text = "cached property"
        hyperlink = nodes.reference("", "", nodes.Text(link_text), refuri=uri)

        # Creating the paragraph and adding the intro text and hyperlink
        para = nodes.paragraph("", "")
        para += nodes.Text(pre_text, pre_text)
        para += hyperlink
        para += nodes.Text(post_text, post_text)

        # Add the paragraph to the admonition
        admonition_node += para

        # Return the target node and the admonition node as the directive's output
        return [targetnode, admonition_node]


def setup(app):
    app.add_directive("cached_property_note", CachedPropertyDirective)
