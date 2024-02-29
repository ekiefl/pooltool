from __future__ import annotations

from abc import ABC, abstractmethod

from attrs import define, evolve, field


@define
class NullObject:
    """A null object

    Attributes:
        id: Object ID.
    """

    id: str = field(default="dummy")

    def copy(self) -> NullObject:
        return evolve(self)


class Render(ABC):
    def __init__(self):
        """A base class for rendering physical pool objects

        This class stores base operations on panda3d nodes that are associated with any
        pool objects such as cues, tables, and balls.

        Notes
        =====
        - All nodes for a given object (e.g. table) are stored in self.nodes.
        - Each method decorated with 'abstractmethod' must be defined by the child
          class. The decorator _ensures_ this happens.
        """

        self.nodes = {}
        self.rendered = False

    def remove_node(self, name):
        self.nodes[name].removeNode()
        del self.nodes[name]

    def remove_nodes(self):
        for node in self.nodes.values():
            node.removeNode()

        self.nodes = {}
        self.rendered = False

    def hide_node(self, name):
        self.nodes[name].hide()

    def hide_nodes(self, ignore=set()):
        for node_name in self.nodes:
            if node_name in ignore:
                continue
            self.hide_node(node_name)

    def show_node(self, name):
        self.nodes[name].show()

    def show_nodes(self, ignore=set()):
        for node_name in self.nodes:
            if node_name in ignore:
                continue
            self.show_node(node_name)

    def get_node(self, name):
        return self.nodes[name]

    @abstractmethod
    def get_render_state(self):
        pass

    @abstractmethod
    def render(self):
        self.rendered = True
