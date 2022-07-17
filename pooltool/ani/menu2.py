#! /usr/bin/env python

import sys
import configparser
from panda3d.core import *
from direct.gui.DirectGui import *
import xml.etree.ElementTree as ET
from direct.showbase.ShowBase import ShowBase

from pooltool.utils import panda_path
import pooltool
import pooltool.ani as ani
import pooltool.ani.utils as autils
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TransparencyAttrib

from pathlib import Path

TEXT_COLOR = (0.1, 0.1, 0.1, 1)
FRAME_COLOR = (0, 0, 0, 1)
TEXT_SCALE = 0.05
BUTTON_TEXT_SCALE = 0.07
AUX_TEXT_SCALE = BUTTON_TEXT_SCALE*1.0
BACKBUTTON_TEXT_SCALE = 0.06
HEADING_SCALE = 0.12
SUBHEADING_SCALE = 0.08
MOVE = 0.02
INFO_SCALE = 0.025
INFO_TEXT_SCALE = 0.05
MENU_ASSETS = ani.model_dir / 'menu'
TITLE_FONT = MENU_ASSETS/'fonts'/'labtop-secundo'/'LABTSECW.ttf'
BUTTON_FONT = MENU_ASSETS/'fonts'/'labtop-secundo'/'LABTSECW.ttf'


class XMLMenu(object):
    def __init__(self, path):
        self.path = panda_path(path)
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()


    def iterate_menus(self):
        for menu in self.root:
            yield menu


class Menu(object):
    def __init__(self, xml):
        self.xml = xml
        self.name = self.xml.attrib['name']

        self.title_font = loader.loadFont(panda_path(TITLE_FONT))
        self.button_font = loader.loadFont(panda_path(BUTTON_FONT))

        # No idea why this conditional must exist
        if self.title_font.get_num_pages() == 0:
            self.title_font.setPixelsPerUnit(90)

        self.last_element = None
        self.num_elements = 0
        self.elements = []

        self.area_backdrop = DirectFrame(
            frameColor = FRAME_COLOR,
            frameSize = (-1, 1, -1, 1),
            parent = render2d,
        )

        self.area_backdrop.setImage(panda_path(MENU_ASSETS/'menu_background.jpeg'))
        img = OnscreenImage(
            image=panda_path(ani.logo_paths['default']),
            pos=(0,0,0.65),
            parent=self.area_backdrop,
            scale=(1.4*0.25, 1, 1.4*0.22)
        )
        img.setTransparency(TransparencyAttrib.MAlpha)

        self.area = DirectScrolledFrame(
            frameColor = (1, 1, 1, 0.2), # alpha == 0
            canvasSize=(-1, 1, -3, 1),
            frameSize=(-1, 1, -0.9, 0.3),
            scrollBarWidth=0.04,
            horizontalScroll_frameSize=(0, 0, 0, 0),
            parent=aspect2d,
        )
        self.area.setPos(0, 0, 0)
        self.area.setTransparency(TransparencyAttrib.MAlpha)

        # 0.05 means you scroll from top to bottom in 20 discrete steps
        self.area.verticalScroll['pageSize'] = 0.05

        self.hovered_entry = None


    def populate(self):
        """Populate a menu and hide it"""
        # Loop through each item in the menu's XML, and based on the item's tag, add it
        # to the menu using the corresponding method. Complain if the tag is unknown
        item_to_method = {
            'title': self.add_title,
            'subtitle': self.add_subtitle,
            'dropdown': self.add_dropdown,
            'checkbox': self.add_checkbox,
            'button': self.add_button,
            'backbutton': self.add_backbutton,
            'text': self.add_text,
            'entry': self.add_entry,
        }
        for item in self.xml:
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
            text = item.text,
            scale = HEADING_SCALE,
            parent = self.area.getCanvas(),
            relief = None,
            text_fg = TEXT_COLOR,
            text_align = TextNode.ALeft,
            text_font = self.title_font,
        )

        if self.last_element:
            autils.alignTo(title, self.last_element, autils.CT, autils.CB, gap=(1,1))
        else:
            title.setPos((-0.8, 0, 0.8))
        title.setX(-0.8)

        # Underscore
        title_x, title_y, title_z = title.getPos()
        lines = LineSegs()
        lines.setColor(TEXT_COLOR)
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE*0.2)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE*0.2)
        lines.setThickness(2)
        node = lines.create()
        underscore = NodePath(node)
        underscore.reparentTo(self.area.getCanvas())

        # Invisible line for white space
        lines = LineSegs()
        lines.setColor((0,0,0,0))
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE*0.5)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE*0.5)
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

        self.elements.append({
            'type': 'title',
            'name': item.text,
            'content': title_obj,
        })

        return title_obj


    def add_subtitle(self, item):
        """Add a subtitle"""

        title = DirectLabel(
            text = item.text,
            scale = SUBHEADING_SCALE,
            parent = self.area.getCanvas(),
            relief = None,
            text_fg = TEXT_COLOR,
            text_align = TextNode.ALeft,
            text_font = self.title_font,
        )

        if self.last_element:
            autils.alignTo(title, self.last_element, autils.CT, autils.CB, gap=(1,1))
        else:
            title.setPos((-0.77, 0, 0.8))
        title.setX(-0.77)

        # Underscore
        title_x, title_y, title_z = title.getPos()
        lines = LineSegs()
        lines.setColor(TEXT_COLOR)
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE*0.2)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE*0.2)
        lines.setThickness(1)
        node = lines.create()
        underscore = NodePath(node)
        underscore.reparentTo(self.area.getCanvas())

        # Invisible line for white space
        lines = LineSegs()
        lines.setColor((0,0,0,0))
        lines.moveTo(title_x, 0, title_z - HEADING_SCALE*0.5)
        lines.drawTo(0.8, 0, title_z - HEADING_SCALE*0.5)
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

        self.elements.append({
            'type': 'subtitle',
            'name': item.text,
            'content': title_obj,
        })

        return title_obj


    def add_dropdown(self, item):
        name = self.search_child_tag(item, 'name').text
        desc = self.search_child_tag(item, 'description').text

        if item.attrib.get('from_yaml'):
            # Populate the options from a YAML
            path = Path(pooltool.__file__).parent / item.attrib.get('from_yaml')
            config_obj = configparser.ConfigParser()
            config_obj.read(path)
            options = [option for option in config_obj.sections()]
        else:
            # Read the options directly from the XML
            options = [subitem.text for subitem in item if subitem.tag == 'option']

        try:
            func_name = self.search_child_tag(item, 'func').text
        except ValueError:
            func_name = None

        title = DirectLabel(
            text = name + ":",
            scale = AUX_TEXT_SCALE,
            parent = self.area.getCanvas(),
            relief = None,
            text_fg = TEXT_COLOR,
            text_align = TextNode.ALeft,
            text_font = self.title_font,
        )
        title.reparentTo(self.area.getCanvas())
        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        dropdown = DirectOptionMenu(
            scale=BUTTON_TEXT_SCALE*0.8,
            items=options,
            highlightColor=(0.65, 0.65, 0.65, 1),
            textMayChange=1,
            text_align = TextNode.ALeft,
            #text_font = self.button_font,
            relief=DGG.RIDGE,
            popupMarker_scale=0.6,
            popupMarker_image=loadImageAsPlane(panda_path(MENU_ASSETS/'dropdown_marker.png')),
            popupMarker_relief=None,
            item_pad=(0.2,0.2),
        )
        dropdown['frameColor'] = (1, 1, 1, 0.3)
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
            text = '',
            text_align = TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS/'info_button.png'),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs = [desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, title_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # Create a parent for all the nodes
        dropdown_id = 'dropdown_' + item.text.replace(' ', '_')
        dropdown_obj = self.area.getCanvas().attachNewNode(dropdown_id)
        title_np.reparentTo(dropdown_obj)
        dropdown_np.reparentTo(dropdown_obj)
        info_button.reparentTo(dropdown_obj)

        self.last_element = dropdown_np

        self.elements.append({
            'type': 'dropdown',
            'name': name,
            'content': dropdown_obj,
            'object': dropdown,
            'convert_factor': None,
            'func_name': func_name,
        })


    def add_checkbox(self, item):
        name = self.search_child_tag(item, 'name').text
        desc = self.search_child_tag(item, 'description').text

        title = DirectLabel(
            text = name + ":",
            scale = AUX_TEXT_SCALE,
            parent = self.area.getCanvas(),
            relief = None,
            text_fg = TEXT_COLOR,
            text_align = TextNode.ALeft,
            text_font = self.title_font,
        )
        title.reparentTo(self.area.getCanvas())
        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        checkbox = DirectCheckButton(
            scale=BUTTON_TEXT_SCALE*0.5,
            boxImage=(
              panda_path(MENU_ASSETS/'unchecked.png'),  
              panda_path(MENU_ASSETS/'checked.png'),  
              None,  
            ),
            text="",
            relief=None,
            boxRelief=None,
        )

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
            text = '',
            text_align = TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS/'info_button.png'),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs = [desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, title_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # Create a parent for all the nodes
        checkbox_id = 'checkbox_' + item.text.replace(' ', '_')
        checkbox_obj = self.area.getCanvas().attachNewNode(checkbox_id)
        title_np.reparentTo(checkbox_obj)
        checkbox_np.reparentTo(checkbox_obj)
        info_button.reparentTo(checkbox_obj)

        self.last_element = checkbox_np

        self.elements.append({
            'type': 'checkbox',
            'name': name,
            'content': checkbox_obj,
            'object': checkbox,
            'convert_factor': None,
        })


    def add_entry(self, item):
        name = self.search_child_tag(item, 'name').text
        desc = self.search_child_tag(item, 'description').text

        try:
            initial = item.attrib['initial']
        except KeyError:
            initial = ''

        try:
            width = int(item.attrib['width'])
        except KeyError:
            width = 4

        title = DirectLabel(
            text = name + ":",
            scale = AUX_TEXT_SCALE,
            parent = self.area.getCanvas(),
            relief = None,
            text_fg = TEXT_COLOR,
            text_align = TextNode.ALeft,
            text_font = self.title_font,
        )
        title.reparentTo(self.area.getCanvas())
        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        entry = DirectEntry(
            text = "",
            scale = BUTTON_TEXT_SCALE*0.7,
            initialText = initial,
            relief=DGG.RIDGE,
            numLines = 1,
            width = width,
            focus = 0,
            focusInCommand = self.set_entry_focus,
            focusInExtraArgs = [True, name],
            #focusOutCommand = self.set_entry_focus,
            #focusOutExtraArgs = [False, name],
            suppressKeys = True,
        )
        entry['frameColor'] = (1, 1, 1, 0.3)

        # If the mouse hovers over a direct entry, update self.hovered_entry
        entry.bind(DGG.ENTER, self.update_hovered_entry, extraArgs = [name])
        entry.bind(DGG.EXIT, self.update_hovered_entry, extraArgs = [None])

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
            text = '',
            text_align = TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS/'info_button.png'),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs = [desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, title_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # Create a parent for all the nodes
        entry_id = 'entry_' + item.text.replace(' ', '_')
        entry_obj = self.area.getCanvas().attachNewNode(entry_id)
        title_np.reparentTo(entry_obj)
        entry_np.reparentTo(entry_obj)
        info_button.reparentTo(entry_obj)

        self.last_element = entry_np

        self.elements.append({
            'type': 'entry',
            'name': name,
            'content': entry_obj,
            'object': entry,
            'convert_factor': None,
        })


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


    def set_entry_focus(self, value, name):
        """Set DirectEntry __dict__ value 'focus' to True if it has focus

        While the focus of a DirectEntry can be set programmatically by updating
        DirectEntry['focus'], when the focus is via the user (clicking), this dictionary
        is not updated. This undesirable behavior is ironed out here. Whenever a
        DirectEntry is given focus, this method is called, which updates the dictionary.
        """
        for element in self.elements:
            if element['type'] == 'entry' and element['name'] == name:
                element['object']['focus'] = value
                return


    def add_button(self, item):
        """Add a button"""

        name = self.search_child_tag(item, 'name').text
        func_name = self.search_child_tag(item, 'func').text
        desc = self.search_child_tag(item, 'description').text

        # This is the button you click. NOTE `command` is assigned ad hoc. See
        # Menus.populate_menus
        button = DirectButton(
            text = name,
            text_align = TextNode.ALeft,
            text_font = self.button_font,
            scale=BUTTON_TEXT_SCALE,
            geom=loadImageAsPlane(panda_path(MENU_ASSETS/'button.png')),
            relief=None,
        )

        # Bind mouse hover to highlighting option
        button.bind(DGG.ENTER, self.highlight_button, extraArgs = [button])
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
            text = '',
            text_align = TextNode.ALeft,
            scale=INFO_SCALE,
            image=panda_path(MENU_ASSETS/'info_button.png'),
            relief=None,
        )

        # Bind mouse hover to displaying button info
        info_button.bind(DGG.ENTER, self.display_button_info, extraArgs = [desc])
        info_button.bind(DGG.EXIT, self.destroy_button_info)

        info_button = NodePath(info_button)
        info_button.reparentTo(self.area.getCanvas())

        # Align the info button next to the button it refers to
        autils.alignTo(info_button, button_np, autils.CR, autils.CL)
        # Then shift it over just a bit to give some space
        info_button.setX(info_button.getX() - 0.02)

        # Create a parent for all the nodes
        button_id = 'button_' + item.text.replace(' ', '_')
        button_obj = self.area.getCanvas().attachNewNode(button_id)
        button_np.reparentTo(button_obj)
        info_button.reparentTo(button_obj)

        self.last_element = button_np

        self.elements.append({
            'type': 'button',
            'name': name,
            'content': button_obj,
            'object': button,
            'convert_factor': None,
            'func_name': func_name,
        })

        return button_obj


    def add_backbutton(self, item):
        """Add a back button"""

        func_name = item[0].text

        # This is the button you click. NOTE `command` is assigned ad hoc. See
        # Menus.populate_menus
        button = DirectButton(
            scale=BACKBUTTON_TEXT_SCALE,
            geom=(
                loadImageAsPlane(panda_path(MENU_ASSETS/'backbutton.png')),
                loadImageAsPlane(panda_path(MENU_ASSETS/'backbutton.png')),
                loadImageAsPlane(panda_path(MENU_ASSETS/'backbutton_hover.png')),
                loadImageAsPlane(panda_path(MENU_ASSETS/'backbutton.png')),
            ),
            relief=None,
        )

        button_np = NodePath(button)
        # functional_button-<menu_name>-<button_text>
        button_id = f"functional_button-{self.name}-back"
        button_np.setName(button_id)
        button_np.reparentTo(self.area)

        button_np.setPos(-0.92, 0, 0.22)

        self.elements.append({
            'type': 'backbutton',
            'content': button_np,
            'object': button,
            'func_name': func_name,
        })

        return button_np


    def add_text(self, item):
        """Add text"""

        text = item.text.strip()
        max_len = 55
        new_text = []
        line, columns = [], 0
        for word in text.split():
            if columns + len(word) > max_len:
                new_text.append(' '.join(line))
                line, columns = [], 0
            columns += len(word)
            line.append(word)
        new_text.append(' '.join(line))
        text = '\n'.join(new_text)

        text_obj = DirectLabel(
            text = text,
            scale = TEXT_SCALE,
            parent = self.area.getCanvas(),
            relief = None,
            text_fg = TEXT_COLOR,
            text_align = TextNode.ALeft,
            text_font = None,
        )

        if self.last_element:
            autils.alignTo(text_obj, self.last_element, autils.CT, autils.CB, gap=(1,1))
        else:
            text_obj.setPos((-0.7, 0, 0.8))
        text_obj.setX(-0.7)

        self.last_element = text_obj

        self.elements.append({
            'type': 'text',
            'text': text,
            'content': text_obj,
        })

        return text_obj


    def highlight_button(self, button, mouse_watcher):
        self.highlighted_menu_button = button
        self.highlighted_menu_button.setScale(self.highlighted_menu_button.getScale() * 11/10)


    def unhighlight_button(self, mouse_watcher):
        self.highlighted_menu_button.setScale(self.highlighted_menu_button.getScale() * 10/11)


    def display_button_info(self, msg, mouse_watcher):
        self.hover_msg = DirectLabel(
            frameColor = (1,1,0.9,1),
            text = msg,
            scale = INFO_TEXT_SCALE,
            parent = aspect2d,
            text_fg = TEXT_COLOR,
            text_align = TextNode.ALeft,
            pad=(0.2,0.2),
        )

        # Position the hover message at the mouse
        coords = mouse_watcher.getMouse()
        r2d = Point3(coords[0], 0, coords[1])
        a2d = aspect2d.getRelativePoint(render2d, r2d)
        self.hover_msg.setPos(a2d)
        # Now shift it up so the mouse doesn't get in the way
        self.hover_msg.setZ(self.hover_msg.getZ() + INFO_SCALE*2)


    def destroy_button_info(self, coords):
        self.hover_msg.removeNode()


    def get(self, name):
        for element in self.elements:
            if element['name'] == name:
                return element['content']


    def names(self):
        return set([x['name'] for x in self.elements])


    def hide(self):
        self.area_backdrop.hide()
        self.area.hide()


    def show(self):
        self.area_backdrop.show()
        self.area.show()


class Menus(object):
    def __init__(self):
        self.menus = {}
        menu_xml_path = Path(pooltool.__file__).parent / 'config' / 'menus.xml'
        self.xml = XMLMenu(path=menu_xml_path)
        self.current_menu = None
        self.populate_menus()

        self.show_menu('main_menu')


    def populate_menus(self):
        """Populate all menus"""
        for menu_xml in self.xml.iterate_menus():
            menu = Menu(menu_xml)
            menu.populate()
            self.menus[menu.name] = menu

        # Now we do something hacky. We go through the menus again, and assign the
        # functions belonging to all the buttons/elements. This happens because the Menu
        # objects do not have access to the global(ly) namespace where some of the
        # functions exist. By assigning them from here, we can bind the functions we
        # need.

        for menu_xml in self.xml.iterate_menus():
            menu_name = menu_xml.attrib['name']
            menu = self.menus[menu_name]
            for element in menu.elements:
                func_name = element.get('func_name')
                if func_name:
                    # This GUI element has a function pending association with it. Find
                    # the function and attribute it to the element.
                    element['object']['command'] = getattr(self, func_name)


    def show_menu(self, name):
        self.hide_menus()
        self.menus[name].show()
        self.current_menu = self.menus[name]


    def hide_menus(self):
        for menu_name, menu in self.menus.items():
            self.menus[menu_name].hide()

        self.current_menu = None


    def get_menu_options(self):
        # FIXME
        return {}


    def func_null(self, *args):
        return


    def func_quit_pooltool(self):
        sys.exit()


    def func_save_table(self):
        # FIXME
        print('Table saved!')


    def func_go_about(self):
        self.show_menu('about')


    def func_go_game_setup(self):
        self.show_menu('game_setup')


    def func_go_new_table(self):
        self.show_menu('new_table')


    def func_go_settings(self):
        self.show_menu('settings')


    def func_go_main_menu(self):
        self.show_menu('main_menu')


def loadImageAsPlane(filepath, yresolution = 600):
	"""
	Load image as 3d plane
	
	Arguments:
	filepath -- image file path
	yresolution -- pixel-perfect width resolution
	"""
	
	tex = loader.loadTexture(filepath)
	tex.setBorderColor(Vec4(0,0,0,0))
	tex.setWrapU(Texture.WMBorderColor)
	tex.setWrapV(Texture.WMBorderColor)
	cm = CardMaker(filepath + ' card')
	cm.setFrame(-tex.getOrigFileXSize(), tex.getOrigFileXSize(), -tex.getOrigFileYSize(), tex.getOrigFileYSize())
	card = NodePath(cm.generate())
	card.setTexture(tex)
	card.setScale(card.getScale()/ yresolution)
	card.flattenLight() # apply scale
	return card


