#! /usr/bin/env python

import sys
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
TEXT_SCALE = 0.04
BUTTON_TEXT_SCALE = 0.07
HEADING_SCALE = 0.12
SUBHEADING_SCALE = 0.09
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
            canvasSize=(-1, 1, -2, 1),
            frameSize=(-1, 1, -0.9, 0.3),
            scrollBarWidth=0.04,
            horizontalScroll_frameSize=(0, 0, 0, 0),
            parent=aspect2d,
        )
        self.area.setPos(0, 0, 0)
        self.area.setTransparency(TransparencyAttrib.MAlpha)

        # 0.05 means you scroll from top to bottom in 20 discrete steps
        self.area.verticalScroll['pageSize'] = 0.05


    def populate(self):
        """Populate a menu and hide it"""
        # Loop through each item in the menu's XML, and based on the item's tag, add it
        # to the menu using the corresponding method. Complain if the tag is unknown
        item_to_method = {
            'title': self.add_title,
            'button': self.add_button,
            'text': self.add_text,
        }
        for item in self.xml:
            method = item_to_method.get(item.tag)
            if method is None:
                raise ValueError(f"Unknown tag '{item.tag}'")
            method(item)

        self.hide()


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


    def add_button(self, item):
        """Add a button"""

        name = item[0].text
        func_name = item[1].text
        desc = item[2].text

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


    def add_text(self, item):
        """Add text"""

        text = item.text.strip()
        max_len = 60
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
        self.hover_msg.setZ(self.hover_msg.getZ() + INFO_SCALE)


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


    def func_null(self):
        return


    def func_quit_pooltool(self):
        sys.exit()


    def func_go_about(self):
        self.show_menu('about')


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


