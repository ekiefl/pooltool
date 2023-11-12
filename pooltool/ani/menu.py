"""FIXME Complete rework necessary. From scratch might be best. XML could be good but
maybe YAML is best. Perhaps starting with the desired dataclasses would be best, and
then serializing them to determine the output format"""

import configparser
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple

from direct.gui.DirectGui import (
    DGG,
    DirectButton,
    DirectCheckButton,
    DirectEntry,
    DirectFrame,
    DirectLabel,
    DirectOptionMenu,
    DirectScrolledFrame,
)
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import (
    CardMaker,
    LineSegs,
    NodePath,
    Point3,
    TextNode,
    Texture,
    TransparencyAttrib,
    Vec4,
)

import pooltool
import pooltool.ani as ani
import pooltool.ani.utils as autils
from pooltool.ani.fonts import load_font
from pooltool.ani.globals import Global
from pooltool.utils import panda_path

TEXT_COLOR = (0.1, 0.1, 0.1, 1)
FRAME_COLOR = (0, 0, 0, 1)
TEXT_SCALE = 0.05
BUTTON_TEXT_SCALE = 0.07
AUX_TEXT_SCALE = BUTTON_TEXT_SCALE * 1.0
ERROR_TEXT_SCALE = BUTTON_TEXT_SCALE * 0.6
ERROR_COLOR = (0.9, 0.4, 0.4, 1)
BACKBUTTON_TEXT_SCALE = 0.06
HEADING_SCALE = 0.12
SUBHEADING_SCALE = 0.08
MOVE = 0.02
INFO_SCALE = 0.025
INFO_TEXT_SCALE = 0.05
MENU_ASSETS = ani.model_dir / "menu"
TITLE_FONT = "LABTSECW"
BUTTON_FONT = "LABTSECW"


class XMLMenu:
    def __init__(self):
        menu_dir = Path(pooltool.__file__).parent / "config" / "menus"

        self.paths = {}
        self.trees = {}
        self.roots = {}

        for xml_path in menu_dir.glob("*.xml"):
            tree = ET.parse(xml_path)
            root = tree.getroot()
            name = root.attrib["name"]

            self.paths[name] = xml_path
            self.trees[name] = tree
            self.roots[name] = root

    def iterate_menus(self):
        for menu in self.roots.values():
            yield menu

    def write(self, path=None):
        for name in self.paths:
            self.trees[name].write(self.paths[name])


class Menu:
    def __init__(self, xml, name):
        self.xml = xml
        self.name = name
        self.menu_xml = self.get_xml()

        self.title_font = load_font(TITLE_FONT)
        self.button_font = load_font(BUTTON_FONT)

        # This is necessary, but unexplainable
        if self.title_font.get_num_pages() == 0:
            self.title_font.setPixelsPerUnit(90)

        self.last_element = None
        self.num_elements = 0
        self.elements = []

        self.area_backdrop = DirectFrame(
            frameColor=FRAME_COLOR,
            frameSize=(-1, 1, -1, 1),
            parent=Global.render2d,
        )

        self.area_backdrop.setImage(panda_path(MENU_ASSETS / "menu_background.jpeg"))
        img = OnscreenImage(
            image=panda_path(ani.logo_paths["default"]),
            pos=(0, 0, 0.65),
            parent=self.area_backdrop,
            scale=(1.4 * 0.25, 1, 1.4 * 0.22),
        )
        img.setTransparency(TransparencyAttrib.MAlpha)

        self.area = DirectScrolledFrame(
            frameColor=(1, 1, 1, 0.2),  # alpha == 0
            canvasSize=(-1, 1, -3, 1),
            frameSize=(-1, 1, -0.9, 0.3),
            scrollBarWidth=0.04,
            horizontalScroll_frameSize=(0, 0, 0, 0),
            parent=Global.aspect2d,
        )
        self.area.setPos(0, 0, 0)
        self.area.setTransparency(TransparencyAttrib.MAlpha)

        # 0.05 means you scroll from top to bottom in 20 discrete steps
        self.area.verticalScroll["pageSize"] = 0.05

        self.hovered_entry = None

    def _update_xml(func):
        def inner(self, *args, **kwargs):
            output = func(self, *args, **kwargs)
            self.xml.write()
            return output

        return inner

    def get_xml(self):
        for menu in self.xml.iterate_menus():
            if menu.attrib["name"] == self.name:
                break
        else:
            raise ValueError(f"Can't get XML for menu name '{self.name}'")

        return menu

    def populate(self):
        """Populate a menu and hide it"""
        # Loop through each item in the menu's XML, and based on the item's tag, add it
        # to the menu using the corresponding method. Complain if the tag is unknown
        item_to_method = {
            "title": self.add_title,
            "subtitle": self.add_subtitle,
            "dropdown": self.add_dropdown,
            "checkbox": self.add_checkbox,
            "button": self.add_button,
            "backbutton": self.add_backbutton,
            "text": self.add_text,
            "entry": self.add_entry,
        }

        for item in self.menu_xml:
            method = item_to_method.get(item.tag)
            if method is None:
                raise ValueError(f"Unknown tag '{item.tag}'")
            method(item)

        self.hide()

    def search_child_tag(self, item, tag):
        """Return first child within xml item with given tag. Error if absent"""
        for subitem in item:
            if subitem.tag == tag:
                return subitem
        else:
            raise ValueError(f"{item} has no child with tag '{tag}'")

    def add_title(self, item):
        """Add a title"""

        title = DirectLabel(
            text=item.text,
            scale=HEADING_SCALE,
            parent=self.area.getCanvas(),
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=self.title_font,
        )

        if self.last_element:
            autils.alignTo(title, self.last_element, autils.CT, autils.CB, gap=(1, 1))
        else:
            title.setPos((-0.8, 0, 0.8))
        title.setX(-0.8)

        # Underscore
        title_x, title_y, title_z = title.getPos()
        lines = LineSegs()
        lines.setColor(TEXT_COLOR)
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE * 0.2)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE * 0.2)
        lines.setThickness(2)
        node = lines.create()
        underscore = NodePath(node)
        underscore.reparentTo(self.area.getCanvas())

        # Invisible line for white space
        lines = LineSegs()
        lines.setColor((0, 0, 0, 0))
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE * 0.5)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE * 0.5)
        lines.setThickness(2)
        node = lines.create()
        whitespace = NodePath(node)
        whitespace.reparentTo(self.area.getCanvas())

        # Create a parent for all the nodes
        title_obj = self.area.getCanvas().attachNewNode(f"title_{self.name}")
        title.reparentTo(title_obj)
        underscore.reparentTo(title_obj)
        whitespace.reparentTo(title_obj)

        self.last_element = title_obj

        self.elements.append(
            {
                "type": "title",
                "name": item.text,
                "content": title_obj,
                "xml": item,
            }
        )

        return title_obj

    def add_subtitle(self, item):
        """Add a subtitle"""

        name = item.attrib.get("name", "")

        title = DirectLabel(
            text=item.text,
            scale=SUBHEADING_SCALE,
            parent=self.area.getCanvas(),
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=self.title_font,
        )

        if self.last_element:
            autils.alignTo(title, self.last_element, autils.CT, autils.CB, gap=(1, 1))
        else:
            title.setPos((-0.77, 0, 0.8))
        title.setX(-0.77)

        # Underscore
        title_x, title_y, title_z = title.getPos()
        lines = LineSegs()
        lines.setColor(TEXT_COLOR)
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE * 0.2)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE * 0.2)
        lines.setThickness(1)
        node = lines.create()
        underscore = NodePath(node)
        underscore.reparentTo(self.area.getCanvas())

        # Invisible line for white space
        lines = LineSegs()
        lines.setColor((0, 0, 0, 0))
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE * 0.5)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE * 0.5)
        lines.setThickness(1)
        node = lines.create()
        whitespace = NodePath(node)
        whitespace.reparentTo(self.area.getCanvas())

        # Create a parent for all the nodes
        title_obj = self.area.getCanvas().attachNewNode(f"title_{self.name}")
        title.reparentTo(title_obj)
        underscore.reparentTo(title_obj)
        whitespace.reparentTo(title_obj)

        self.last_element = title_obj

        self.elements.append(
            {
                "type": "subtitle",
                "name": name,
                "object": title_obj,
                "content": title,
                "xml": item,
            }
        )

        return title_obj

    def add_dropdown(self, item):
        name = self.search_child_tag(item, "name").text
        desc = self.search_child_tag(item, "description").text

        if item.attrib.get("from_yaml"):
            # Populate the options from a YAML
            path = Path(pooltool.__file__).parent / item.attrib.get("from_yaml")
            config_obj = configparser.ConfigParser()
            config_obj.read(path)
            options = [option for option in config_obj.sections()]
        else:
            # Read the options directly from the XML
            options = [subitem.text for subitem in item if subitem.tag == "option"]

        initial_option = item.attrib["selection"]

        try:
            func_name = self.search_child_tag(item, "func").text
        except ValueError:
            func_name = "func_update_dropdown_xml"

        title = DirectLabel(
            text=name + ":",
            scale=AUX_TEXT_SCALE,
            parent=self.area.getCanvas(),
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=self.title_font,
        )
        title.reparentTo(self.area.getCanvas())
        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        dropdown = DirectOptionMenu(
            scale=BUTTON_TEXT_SCALE * 0.8,
            items=options,
            highlightColor=(0.65, 0.65, 0.65, 1),
            textMayChange=1,
            text_align=TextNode.ALeft,
            relief=DGG.RIDGE,
            initialitem=options.index(initial_option),
            popupMarker_scale=0.6,
            popupMarker_image=loadImageAsPlane(
                panda_path(MENU_ASSETS / "dropdown_marker.png")
            ),
            popupMarker_relief=None,
            item_pad=(0.2, 0.2),
        )
        dropdown["frameColor"] = (1, 1, 1, 0.3)
        dropdown["extraArgs"] = [item.attrib["name"]]
        dropdown.reparentTo(self.area.getCanvas())

        dropdown_np = NodePath(dropdown)
        # functional_dropdown-<menu_name>-<dropdown_text>
        dropdown_id = f"functional_dropdown-{self.name}-{name.replace(' ','_')}"
        dropdown_np.setName(dropdown_id)
        dropdown_np.reparentTo(self.area.getCanvas())

        if self.last_element:
            autils.alignTo(title_np, self.last_element, autils.CT, autils.CB)
        else:
            title_np.setPos(-0.63, 0, 0.8)
        title_np.setX(-0.63)
        title_np.setZ(title_np.getZ() - MOVE)

        # Align the dropdown next to the title that refers to it
        autils.alignTo(dropdown_np, title_np, autils.CL, autils.CR)
        # Then shift it over just a bit to give some space
        dropdown_np.setX(dropdown_np.getX() + 0.02)
        # Then shift it down a little to align the text
        dropdown_np.setZ(dropdown_np.getZ() - 0.005)

        # This is the info button you hover over
        info_button = DirectButton(
            text="",
            text_align=TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS / "info_button.png"),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs=[desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, title_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # Create a parent for all the nodes
        dropdown_id = "dropdown_" + item.text.replace(" ", "_")
        dropdown_obj = self.area.getCanvas().attachNewNode(dropdown_id)
        title_np.reparentTo(dropdown_obj)
        dropdown_np.reparentTo(dropdown_obj)
        info_button.reparentTo(dropdown_obj)

        self.last_element = dropdown_np

        self.elements.append(
            {
                "type": "dropdown",
                "name": item.attrib["name"],
                "content": dropdown_obj,
                "object": dropdown,
                "convert_factor": None,
                "func_name": func_name,
                "xml": item,
            }
        )

    def add_checkbox(self, item):
        name = self.search_child_tag(item, "name").text
        desc = self.search_child_tag(item, "description").text

        try:
            func_name = self.search_child_tag(item, "func").text
        except ValueError:
            func_name = "func_update_checkbox_xml"

        title = DirectLabel(
            text=name + ":",
            scale=AUX_TEXT_SCALE,
            parent=self.area.getCanvas(),
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=self.title_font,
        )
        title.reparentTo(self.area.getCanvas())
        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        checkbox = DirectCheckButton(
            scale=BUTTON_TEXT_SCALE * 0.5,
            boxImage=(
                panda_path(MENU_ASSETS / "unchecked.png"),
                panda_path(MENU_ASSETS / "checked.png"),
                None,
            ),
            text="",
            indicatorValue=1 if item.attrib["checked"] == "true" else 0,
            relief=None,
            boxRelief=None,
        )
        checkbox["extraArgs"] = [item.attrib["name"]]

        checkbox_np = NodePath(checkbox)
        # functional_checkbox-<menu_name>-<checkbox_text>
        checkbox_id = f"functional_checkbox-{self.name}-{name.replace(' ','_')}"
        checkbox_np.setName(checkbox_id)
        checkbox_np.reparentTo(self.area.getCanvas())

        if self.last_element:
            autils.alignTo(title_np, self.last_element, autils.CT, autils.CB)
        else:
            title_np.setPos(-0.63, 0, 0.8)
        title_np.setX(-0.63)
        title_np.setZ(title_np.getZ() - MOVE)

        # Align the checkbox next to the title that refers to it
        autils.alignTo(checkbox_np, title_np, autils.CL, autils.CR)
        # Then shift it over just a bit to give some space
        checkbox_np.setX(checkbox_np.getX() + 0.02)
        # Then shift it down a little to align the text
        checkbox_np.setZ(checkbox_np.getZ() - 0.005)

        # This is the info button you hover over
        info_button = DirectButton(
            text="",
            text_align=TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS / "info_button.png"),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs=[desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, title_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # Create a parent for all the nodes
        checkbox_id = "checkbox_" + item.text.replace(" ", "_")
        checkbox_obj = self.area.getCanvas().attachNewNode(checkbox_id)
        title_np.reparentTo(checkbox_obj)
        checkbox_np.reparentTo(checkbox_obj)
        info_button.reparentTo(checkbox_obj)

        self.last_element = checkbox_np

        self.elements.append(
            {
                "type": "checkbox",
                "name": item.attrib["name"],
                "content": checkbox_obj,
                "object": checkbox,
                "func_name": func_name,
                "xml": item,
                "convert_factor": None,
            }
        )

    def add_entry(self, item):
        name = self.search_child_tag(item, "name").text
        desc = self.search_child_tag(item, "description").text

        validator = item.attrib.get("validator")
        if validator is None:

            def validator(value):
                return True

        else:
            try:
                validator = getattr(self, validator)
            except AttributeError:
                raise AttributeError(
                    f"Unknown validator string '{validator}' for element with name "
                    f"'{name}'"
                )

        try:
            initial = item.attrib["initial"]
        except KeyError:
            initial = ""

        item.attrib["value"] = initial

        try:
            width = int(item.attrib["width"])
        except KeyError:
            width = 4

        title = DirectLabel(
            text=name + ":",
            scale=AUX_TEXT_SCALE,
            parent=self.area.getCanvas(),
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=self.title_font,
        )
        title.reparentTo(self.area.getCanvas())
        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        entry = DirectEntry(
            text="",
            scale=BUTTON_TEXT_SCALE * 0.7,
            initialText=initial,
            relief=DGG.RIDGE,
            numLines=1,
            width=width,
            focus=0,
            focusInCommand=self.entry_buildup,
            focusInExtraArgs=[True, name],
            focusOutCommand=self.entry_teardown,
            focusOutExtraArgs=[name, initial],
            suppressKeys=True,
        )
        entry["frameColor"] = (1, 1, 1, 0.3)

        # If the mouse hovers over a direct entry, update self.hovered_entry
        entry.bind(DGG.ENTER, self.update_hovered_entry, extraArgs=[name])
        entry.bind(DGG.EXIT, self.update_hovered_entry, extraArgs=[None])

        entry_np = NodePath(entry)
        # functional_entry-<menu_name>-<entry_text>
        entry_id = f"functional_entry-{self.name}-{name.replace(' ','_')}"
        entry_np.setName(entry_id)
        entry_np.reparentTo(self.area.getCanvas())

        if self.last_element:
            autils.alignTo(title_np, self.last_element, autils.CT, autils.CB)
        else:
            title_np.setPos(-0.63, 0, 0.8)
        title_np.setX(-0.63)
        title_np.setZ(title_np.getZ() - MOVE)

        # Align the entry next to the title that refers to it
        autils.alignTo(entry_np, title_np, autils.CL, autils.CR)
        # Then shift it over just a bit to give some space
        entry_np.setX(entry_np.getX() + 0.02)
        # Then shift it down a little to align the text
        entry_np.setZ(entry_np.getZ() - 0.005)

        # This is the info button you hover over
        info_button = DirectButton(
            text="",
            text_align=TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS / "info_button.png"),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs=[desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, title_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # This text is shown if an error is detected in the user input
        error = DirectLabel(
            text="",
            textMayChange=1,
            text_fg=ERROR_COLOR,
            text_bg=(0, 0, 0, 0.3),
            scale=ERROR_TEXT_SCALE,
            parent=self.area.getCanvas(),
            relief=None,
            text_align=TextNode.ALeft,
        )
        error.reparentTo(self.area.getCanvas())
        error_np = NodePath(error)
        error_np.reparentTo(self.area.getCanvas())
        error_np.hide()

        # Align the error msg next to the entry it refers to
        autils.alignTo(error, entry_np, autils.CL, autils.CR)
        # Then shift it over just a bit to give some space
        error_np.setX(error_np.getX() + 0.02)
        # And shift it down a little too
        error_np.setZ(error_np.getZ() - 0.01)

        # Create a parent for all the nodes
        entry_id = "entry_" + item.text.replace(" ", "_")
        entry_obj = self.area.getCanvas().attachNewNode(entry_id)
        title_np.reparentTo(entry_obj)
        entry_np.reparentTo(entry_obj)
        info_button.reparentTo(entry_obj)
        error_np.reparentTo(entry_obj)

        self.last_element = entry_np

        self.elements.append(
            {
                "type": "entry",
                "initial": initial,
                "name": name,
                "content": entry_obj,
                "object": entry,
                "error_msg": error,
                "validator": validator,
                "xml": item,
                "convert_factor": None,
            }
        )

        # Call entry teardown for validation
        self.entry_teardown(name, initial)

    def update_hovered_entry(self, name, mouse_watcher):
        """Set self.hovered_entry

        By default, the focus of a DirectEntry can only be unset by pressing 'enter'.
        It feels more natural to unfocus a DirectEntry by clicking outside of the entry,
        so I created an event listener that unfocuses buttons if a click is made. But a
        side effect of this is that any clicks on the entry or undone by this event
        listener. To solve this, I created self.hovered_entry, which is updated every
        time a mouse is over a DirectEntry. The event listener skips over this
        DirectEntry, so that one can click a DirectEntry to gain focus.
        """
        self.hovered_entry = name

    def entry_buildup(self, value, name):
        """Build up operations for entering DirectEntry

        While the focus of a DirectEntry can be set programmatically by updating
        DirectEntry['focus'], when the focus is via the user (clicking), this dictionary
        is not updated. This undesirable behavior is ironed out here. Whenever a
        DirectEntry is given focus, this method is called, which updates the dictionary.
        """

        for element in self.elements:
            if element["type"] == "entry" and element["name"] == name:
                # Clear the entry so user may type on a clean slate
                element["object"].enterText("")

                element["object"]["focus"] = value
                return

    @_update_xml  # type: ignore
    def entry_teardown(self, name, initial):
        """Teardown up operations for leaving DirectEntry"""

        for element in self.elements:
            if element["type"] == "entry" and element["name"] == name:
                value = element["object"].get()

                if value.strip() == "":
                    # The value is empty. Return to initial value
                    element["object"].enterText(initial)
                    value = initial

                # Hide or show error message based on value validity
                valid, reason = element["validator"](value)
                if not valid:
                    element["error_msg"].setText(reason)
                    element["error_msg"].show()
                else:
                    element["error_msg"].setText("")
                    element["error_msg"].hide()

                # Update XML object
                element["xml"].set("value", value)

    def is_entry_floatable(self, value) -> Tuple[bool, str]:
        try:
            float(value)
        except Exception:
            return False, "Error: must be a number"
        else:
            return True, ""

    def is_table_name_valid(self, value) -> Tuple[bool, str]:
        table_names = ani.load_config("tables").keys()
        if value.strip() == "":
            return False, "Error: No name provided"
        if value.strip() in table_names:
            return False, "Error: Table name already exists"
        else:
            return True, ""

    def add_button(self, item):
        """Add a button"""

        name = self.search_child_tag(item, "name").text
        func_name = self.search_child_tag(item, "func").text
        desc = self.search_child_tag(item, "description").text

        # This is the button you click. NOTE `command` is assigned ad hoc. See
        # Menus.populate
        button = DirectButton(
            text=name,
            text_align=TextNode.ALeft,
            text_font=self.button_font,
            scale=BUTTON_TEXT_SCALE,
            geom=loadImageAsPlane(panda_path(MENU_ASSETS / "button.png")),
            relief=None,
        )

        # Bind mouse hover to highlighting option
        button.bind(DGG.ENTER, self.highlight_button, extraArgs=[button])
        button.bind(DGG.EXIT, self.unhighlight_button)

        button_np = NodePath(button)
        # functional_button-<menu_name>-<button_text>
        button_id = f"functional_button-{self.name}-{name.replace(' ','_')}"
        button_np.setName(button_id)
        button_np.reparentTo(self.area.getCanvas())

        if self.last_element:
            autils.alignTo(button_np, self.last_element, autils.CT, autils.CB)
        else:
            button_np.setPos(-0.63, 0, 0.8)
        button_np.setX(-0.63)
        button_np.setZ(button_np.getZ() - MOVE)

        # This is the info button you hover over
        info_button = DirectButton(
            text="",
            text_align=TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS / "info_button.png"),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs=[desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, button_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # Create a parent for all the nodes
        button_id = "button_" + item.text.replace(" ", "_")
        button_obj = self.area.getCanvas().attachNewNode(button_id)
        button_np.reparentTo(button_obj)
        info_button.reparentTo(button_obj)

        self.last_element = button_np

        self.elements.append(
            {
                "type": "button",
                "name": name,
                "content": button_obj,
                "object": button,
                "convert_factor": None,
                "xml": item,
                "func_name": func_name,
            }
        )

        return button_obj

    def add_backbutton(self, item):
        """Add a back button"""

        func_name = item[0].text

        # This is the button you click. NOTE `command` is assigned ad hoc. See
        # Menus.populate
        button = DirectButton(
            scale=BACKBUTTON_TEXT_SCALE,
            geom=(
                loadImageAsPlane(panda_path(MENU_ASSETS / "backbutton.png")),
                loadImageAsPlane(panda_path(MENU_ASSETS / "backbutton.png")),
                loadImageAsPlane(panda_path(MENU_ASSETS / "backbutton_hover.png")),
                loadImageAsPlane(panda_path(MENU_ASSETS / "backbutton.png")),
            ),
            relief=None,
        )

        button_np = NodePath(button)
        # functional_button-<menu_name>-<button_text>
        button_id = f"functional_button-{self.name}-back"
        button_np.setName(button_id)
        button_np.reparentTo(self.area)

        button_np.setPos(-0.92, 0, 0.22)

        self.elements.append(
            {
                "type": "backbutton",
                "content": button_np,
                "object": button,
                "func_name": func_name,
                "xml": item,
            }
        )

        return button_np

    def add_text(self, item):
        """Add text"""

        name = item.attrib.get("name", "")

        text = item.text.strip()
        max_len = 55
        new_text = []
        line, columns = [], 0
        for word in text.split():
            if columns + len(word) > max_len:
                new_text.append(" ".join(line))
                line, columns = [], 0
            columns += len(word)
            line.append(word)
        new_text.append(" ".join(line))
        text = "\n".join(new_text)

        text_obj = DirectLabel(
            text=text,
            scale=TEXT_SCALE,
            parent=self.area.getCanvas(),
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=None,
        )

        if self.last_element:
            autils.alignTo(
                text_obj, self.last_element, autils.CT, autils.CB, gap=(1, 1)
            )
        else:
            text_obj.setPos((-0.7, 0, 0.8))
        text_obj.setX(-0.7)

        self.last_element = text_obj

        self.elements.append(
            {
                "type": "text",
                "name": name,
                "text": text,
                "content": text_obj,
                "xml": item,
            }
        )

        return text_obj

    def highlight_button(self, button, mouse_watcher):
        self.highlighted_menu_button = button
        self.highlighted_menu_button.setScale(
            self.highlighted_menu_button.getScale() * 11 / 10
        )

    def unhighlight_button(self, mouse_watcher):
        self.highlighted_menu_button.setScale(
            self.highlighted_menu_button.getScale() * 10 / 11
        )

    def display_button_info(self, msg, mouse_watcher):
        self.hover_msg = DirectLabel(
            frameColor=(1, 1, 0.9, 1),
            text=msg,
            scale=INFO_TEXT_SCALE,
            parent=Global.aspect2d,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            pad=(0.2, 0.2),
        )

        # Position the hover message at the mouse
        coords = mouse_watcher.getMouse()
        r2d = Point3(coords[0], 0, coords[1])
        a2d = Global.aspect2d.getRelativePoint(Global.render2d, r2d)
        self.hover_msg.setPos(a2d)
        # Now shift it up so the mouse doesn't get in the way
        self.hover_msg.setZ(self.hover_msg.getZ() + INFO_SCALE * 2)

    def destroy_button_info(self, coords):
        self.hover_msg.removeNode()

    def get(self, name):
        for element in self.elements:
            if element["name"] == name:
                return element["content"]

    def names(self):
        return set([x["name"] for x in self.elements])

    def hide(self):
        self.area_backdrop.hide()
        self.area.hide()

    def show(self):
        self.area_backdrop.show()
        self.area.show()


class Menus:
    def __init__(self):
        self.menus = {}
        self.xml = XMLMenu()
        self.current = None

    def _update_xml(func):
        def inner(self, *args, **kwargs):
            output = func(self, *args, **kwargs)
            self.xml.write()
            return output

        return inner

    def populate(self):
        """Populate all menus"""
        for menu_xml in self.xml.iterate_menus():
            name = menu_xml.attrib["name"]
            menu = Menu(self.xml, name)
            menu.populate()
            self.menus[menu.name] = menu

        # Now we do something hacky. We go through the menus again, and assign the
        # functions belonging to all the buttons/elements. This happens because the Menu
        # objects do not have access to the global(ly) namespace where some of the
        # functions exist. By assigning them from here, we can bind the functions we
        # need.

        for menu_xml in self.xml.iterate_menus():
            menu_name = menu_xml.attrib["name"]
            menu = self.menus[menu_name]
            for element in menu.elements:
                func_name = element.get("func_name")
                if func_name:
                    # This GUI element has a function pending association with it. Find
                    # the function and attribute it to the element.
                    element["object"]["command"] = getattr(self, func_name)

    def show(self, name):
        self.hide_all()
        self.menus[name].show()
        self.current = self.menus[name]

    def hide_all(self):
        for menu_name, menu in self.menus.items():
            self.menus[menu_name].hide()

        self.current = None

    def get_options(self):
        return {
            "table_type": self.xml.roots["game_setup"]
            .find(".//*[@name='table_type']")
            .attrib["selection"]
        }

    @_update_xml  # type: ignore
    def func_update_checkbox_xml(self, value, name):
        for element in self.current.elements:
            if element.get("name") == name:
                break
        element["xml"].set("checked", "true" if value == 1 else "false")

    @_update_xml  # type: ignore
    def func_update_dropdown_xml(self, value, name):
        for element in self.current.elements:
            if element.get("name") == name:
                break
        element["xml"].set("selection", value)

    def func_null(self, *args):
        return

    def func_quit_pooltool(self):
        sys.exit()

    def func_save_table(self):
        new_table = {}

        # Add all dropdowns
        for dropdown in self.xml.roots["new_table"].findall(".//dropdown"):
            new_table[dropdown.attrib["name"]] = dropdown.attrib["selection"]

        has_pockets = True if new_table["type"] == "pocket" else False

        # Add the entries
        for entry in self.xml.roots["new_table"].findall(".//entry"):
            pocket_param = (
                False
                if "pocket_param" not in entry.attrib.keys()
                or entry.attrib["pocket_param"] == "false"
                else True
            )
            if not has_pockets and pocket_param:
                continue

            name = entry.attrib["name"]
            value = entry.attrib["value"]
            validator = getattr(self.current, entry.attrib["validator"])

            is_valid, reason = validator(value)
            if not is_valid:
                print(f"{name}: invalid value. {reason}")
                return

            new_table[name] = value

        table_name = new_table.pop("table_name")
        table_config = ani.load_config("tables")
        table_config[table_name] = new_table
        ani.save_config("tables", table_config, overwrite=True)

        # Add new table as option to table
        for element in self.menus["game_setup"].elements:
            if element["type"] == "dropdown" and element["name"] == "table_type":
                tmp_options = element["object"]["items"]
                tmp_options.insert(-1, table_name)
                element["object"]["items"] = tmp_options

    def func_go_about(self):
        self.show("about")

    def func_go_game_setup(self):
        self.show("game_setup")

    def func_go_new_table(self):
        self.show("new_table")

    def func_play_now(self):
        Global.base.messenger.send("enter-game")

    def func_go_view_table(self):
        for element in self.menus["view_table"].elements:
            if element.get("name") == "table_params_name":
                xml = self.menus["game_setup"].xml.roots["game_setup"]
                table_name = xml.find(".//*[@name='table_type']").attrib["selection"]
                element["content"].setText(f"Parameters for '{table_name}'")
            if element.get("name") == "table_params":
                table_dict = ani.load_config("tables")[table_name]
                longest_key = max([len(key) for key in table_dict])
                string = []
                for key, val in table_dict.items():
                    buffer = longest_key - len(key)
                    string.append(key + " " * (buffer + 4) + str(val))
                element["content"].setText("\n".join(string))

        self.show("view_table")

    def func_go_settings(self):
        self.show("settings")

    def func_go_main_menu(self):
        self.show("main_menu")


def loadImageAsPlane(filepath, yresolution=600):
    """
    Load image as 3d plane

    Arguments:
    filepath -- image file path
    yresolution -- pixel-perfect width resolution
    """

    tex = Global.loader.loadTexture(filepath)
    tex.setBorderColor(Vec4(0, 0, 0, 0))
    tex.setWrapU(Texture.WMBorderColor)
    tex.setWrapV(Texture.WMBorderColor)
    cm = CardMaker(filepath + " card")
    cm.setFrame(
        -tex.getOrigFileXSize(),
        tex.getOrigFileXSize(),
        -tex.getOrigFileYSize(),
        tex.getOrigFileYSize(),
    )
    card = NodePath(cm.generate())
    card.setTexture(tex)
    card.setScale(card.getScale() / yresolution)
    card.flattenLight()  # apply scale
    return card


menus = Menus()

# -----------------------------------------------------------------------------------

# FIXME The plan is to remove GenericMenu. It's legacy. GenericMenu should be removed
# and those using GenericMenu should be refactored:
#
# ▶ grep -r "GenericMenu" pooltool/ --exclude="*models*"
#     pooltool//ani/animate.py:from pooltool.ani.menu import GenericMenu
#     pooltool//ani/animate.py:        self.standby_screen = GenericMenu(frame_color=(0.3,0.3,0.3,1))
#     pooltool//ani/modes/cam_save.py:from pooltool.ani.menu import GenericMenu
#     pooltool//ani/modes/cam_save.py:        self.cam_save_slots = GenericMenu(
#     pooltool//ani/modes/calculate.py:from pooltool.ani.menu import GenericMenu
#     pooltool//ani/modes/calculate.py:        self.shot_sim_overlay = GenericMenu(
#     pooltool//ani/modes/game_over.py:from pooltool.ani.menu import GenericMenu
#     pooltool//ani/modes/game_over.py:        self.game_over_menu = GenericMenu(
#     pooltool//ani/modes/cam_load.py:from pooltool.ani.menu import GenericMenu
#     pooltool//ani/modes/cam_load.py:        self.cam_load_slots = GenericMenu(


class GenericMenu:
    def __init__(self, title="", frame_color=(1, 1, 1, 1), title_pos=(0, 0, 0.8)):
        self.titleMenuBackdrop = DirectFrame(
            frameColor=frame_color,
            frameSize=(-1, 1, -1, 1),
            parent=Global.render2d,
        )

        self.text_scale = 0.07
        self.move = 0.12

        self.titleMenu = DirectFrame(frameColor=(1, 1, 1, 0))

        self.title = DirectLabel(
            text=title,
            scale=self.text_scale * 1.5,
            pos=title_pos,
            parent=self.titleMenu,
            relief=None,
            text_fg=(0, 0, 0, 1),
        )

        self.next_x, self.next_y = -0.5, 0.6
        self.num_elements = 0
        self.elements = []

        self.hide()

    def get(self, name):
        for element in self.elements:
            if element["name"] == name:
                return element["content"]

    def names(self):
        return set([x["name"] for x in self.elements])

    def add_button(self, text, command=None, **kwargs):
        """Add a button at a location based on self.next_x and self.next_y"""

        button = make_button(text, command, **kwargs)
        button.reparentTo(self.titleMenu)
        button.setPos((self.next_x, 0, self.next_y))

        self.elements.append(
            {
                "type": "button",
                "name": text,
                "content": button,
                "convert_factor": None,
            }
        )

        self.get_next_pos()

        return button

    def add_image(self, path, pos, scale):
        """Add an image to the menu

        Notes
        =====
        - images are parented to self.titleMenuBackdrop (as opposed self.titleMenu) in
          order to preserve their aspect ratios.
        """

        img = OnscreenImage(
            image=panda_path(path), pos=pos, parent=self.titleMenuBackdrop, scale=scale
        )
        img.setTransparency(TransparencyAttrib.MAlpha)

        self.elements.append(
            {
                "type": "image",
                "name": panda_path(path),
                "content": img,
                "convert_factor": None,
            }
        )

    def add_dropdown(
        self,
        text,
        options=["None"],
        command=None,
        convert_factor=None,
        scale=ani.menu_text_scale,
    ):
        self.get_next_pos(move=self.move / 2)

        dropdown = make_dropdown(text, options, command, scale)
        dropdown.reparentTo(self.titleMenu)
        dropdown.setPos((self.next_x, 0, self.next_y))

        self.elements.append(
            {
                "type": "dropdown",
                "name": text,
                "content": dropdown,
                "convert_factor": convert_factor,
            }
        )

        self.get_next_pos()

    def add_direct_entry(
        self, text, command=None, initial="None", convert_factor=None, scale=None
    ):
        self.get_next_pos(move=self.move / 2)

        direct_entry = make_direct_entry(text, command, scale, initial)
        direct_entry.reparentTo(self.titleMenu)
        direct_entry.setPos((self.next_x, 0, self.next_y))

        self.elements.append(
            {
                "type": "direct_entry",
                "name": text,
                "content": direct_entry,
                "convert_factor": convert_factor,
            }
        )

        self.get_next_pos()

    def get_next_pos(self, move=None):
        if move is None:
            move = self.move

        self.next_y -= move

        if self.next_y <= -1:
            self.next_y = 0.6
            self.next_x += 0.5

        self.num_elements += 1

    def hide(self):
        self.titleMenuBackdrop.hide()
        self.titleMenu.hide()

    def show(self):
        self.titleMenuBackdrop.show()
        self.titleMenu.show()


def make_button(text, command=None, **kwargs):
    return DirectButton(
        text=text, command=command, text_align=TextNode.ACenter, **kwargs
    )


def make_dropdown(text, options=["None"], command=None, scale=ani.menu_text_scale):
    dropdown = DirectOptionMenu(
        scale=scale,
        items=options,
        highlightColor=(0.65, 0.65, 0.65, 1),
        command=command,
        textMayChange=1,
        text_align=TextNode.ALeft,
    )

    DirectLabel(
        text=text + ":",
        relief=None,
        text_fg=(0, 0, 0, 1),
        text_align=TextNode.ALeft,
        parent=dropdown,
        pos=(0, 0, 1),
    )

    return dropdown


def make_direct_entry(text, command=None, scale=ani.menu_text_scale, initial="None"):
    entry = DirectEntry(
        text="",
        scale=scale,
        command=command,
        initialText=initial,
        numLines=1,
        width=4,
        focus=0,
        focusInCommand=lambda: entry.enterText(""),
    )

    DirectLabel(
        text=text + ":",
        relief=None,
        text_fg=(0, 0, 0, 1),
        text_align=TextNode.ALeft,
        parent=entry,
        pos=(0, 0, 1.2),
    )

    return entry
