from docutils import nodes
from sphinx.util.docutils import SphinxDirective

class CachedPropertyDirective(SphinxDirective):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True

    def run(self):
        targetid = f"cached-property-{self.env.new_serialno('cached-property')}"
        targetnode = nodes.target('', '', ids=[targetid])

        # Create an admonition node to hold the content
        admonition_node = nodes.admonition()

        # Optional: Add a title to the admonition
        title_text = "Cached Property Note"
        admonition_node += nodes.title(title_text, title_text)

        # Text before the hyperlink
        pre_text = "This is a "
        post_text = ", and should be accessed as an attribute, not as a method call."

        # Creating the hyperlink
        uri = "https://docs.python.org/3/library/functools.html#functools.cached_property"
        link_text = "cached property"
        hyperlink = nodes.reference('', '', nodes.Text(link_text), refuri=uri)

        # Creating the paragraph and adding the intro text and hyperlink
        para = nodes.paragraph('', '')
        para += nodes.Text(pre_text, pre_text)
        para += hyperlink
        para += nodes.Text(post_text, post_text)

        # Add the paragraph to the admonition
        admonition_node += para

        # Return the target node and the admonition node as the directive's output
        return [targetnode, admonition_node]


class AttrsClassDirective(SphinxDirective):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True

    def run(self):
        targetid = f"attrs-note-{self.env.new_serialno('attrs-note')}"
        targetnode = nodes.target('', '', ids=[targetid])

        # Create an admonition node to hold the content
        admonition_node = nodes.admonition()
        
        # Add a title to the admonition
        title_text = "Attrs Dataclass Note"
        admonition_node += nodes.title(title_text, title_text)
        
        # Create a paragraph node for the content
        para = nodes.paragraph()
        
        # Text before the hyperlink
        pre_text = "This is an "
        para += nodes.Text(pre_text, pre_text)
        
        # Creating the hyperlink
        uri = "https://www.attrs.org/en/stable/examples.html"
        link_text = "attrs dataclass"
        hyperlink = nodes.reference('', '', nodes.Text(link_text), refuri=uri)
        para += hyperlink
        
        # Text after the hyperlink
        post_text = (
            ", and unfortunately pooltool's auto-documentation doesn't provide "
            "clear instructions for how to initialize an attrs dataclass. This note "
            "clarifies how. To create an instance of this class with its "
        )
        para += nodes.Text(post_text, post_text)
        
        # Inline code block
        init_code = "__init__"
        para += nodes.literal(init_code, init_code)
        
        # Continued text
        post_init_text = (
            " method (e.g., "
        )
        para += nodes.Text(post_init_text, post_init_text)
        
        # Example class instantiation (italics for "e.g.")
        example_text = "Class(...)"
        para += nodes.literal(example_text, example_text)
        
        # Final part of the text
        final_text = (
            "), supply its attributes (see below) as arguments. Required arguments "
            "are labeled, optional arguments display their defaults, and attributes "
            "not used for initialization are labeled as 'init = False'"
        )
        para += nodes.Text(final_text, final_text)
        
        # Add the paragraph to the admonition
        admonition_node += para

        return [targetnode, admonition_node]


def setup(app):
    app.add_directive("cached_property_note", CachedPropertyDirective)
    app.add_directive("attrs_note", AttrsClassDirective)
