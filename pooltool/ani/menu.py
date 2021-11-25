#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.games as games

from pooltool.utils import panda_path

import sys

from panda3d.core import *
from direct.gui.DirectGui import *


class Menus(object):
    def __init__(self):
        self.menus = {}
        self.populate_main()
        self.populate_options()
        self.populate_table_options()
        self.populate_ball_options()

        self.current_menu = None


    def populate_main(self):
        m = GenericMenu(title = 'Main Screen')
        m.add_image(ani.logo_paths['small'], pos=(0.7,0,-0.70), scale=(0.25, 1, 0.22))
        m.add_button('New Game', self.go, scale=ani.menu_text_scale)
        m.add_button('Options', lambda: self.show_menu('options'), scale=ani.menu_text_scale)
        m.add_button('Quit', sys.exit, scale=ani.menu_text_scale)

        self.menus['main'] = m


    def populate_options(self):
        m = GenericMenu(title = 'Options')
        m.add_button('Back', lambda: self.show_menu('main'), scale=ani.menu_text_scale)

        m.add_dropdown(ani.options_game, options=list(games.game_classes.keys()))

        m.add_button('Customize table', lambda: self.show_menu('table'), scale=ani.menu_text_scale)
        m.add_button('Customize balls', lambda: self.show_menu('balls'), scale=ani.menu_text_scale)

        self.menus['options'] = m


    def populate_table_options(self):
        m = GenericMenu(title = 'Table customization (SI units)')
        m.add_button('Back', lambda: self.show_menu('options'), scale=ani.menu_text_scale)

        m.add_dropdown(ani.options_table, options=list(ani.table_config.keys()) + ['custom'], command=self.show_custom_table_options)

        m.add_dropdown(ani.options_table_type, options=list(pooltool.objects.table.table_types.keys()), scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_table_length, initial=f"{pooltool.table_length:.5f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_table_width, initial=f"{pooltool.table_width:.5f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_table_height, initial=f"{pooltool.table_height:.5f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_lights_height, initial=f"{pooltool.lights_height:.5f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_cushion_width, initial=f"{pooltool.cushion_width:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_cushion_height, initial=f"{pooltool.cushion_height:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_corner_pocket_width, initial=f"{pooltool.corner_pocket_width:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_corner_pocket_angle, initial=f"{pooltool.corner_pocket_angle:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_corner_pocket_depth, initial=f"{pooltool.corner_pocket_depth:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_corner_pocket_radius, initial=f"{pooltool.corner_pocket_radius:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_corner_jaw_radius, initial=f"{pooltool.corner_jaw_radius:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_side_pocket_width, initial=f"{pooltool.side_pocket_width:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_side_pocket_angle, initial=f"{pooltool.side_pocket_angle:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_side_pocket_depth, initial=f"{pooltool.side_pocket_depth:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_side_pocket_radius, initial=f"{pooltool.side_pocket_radius:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_side_jaw_radius, initial=f"{pooltool.side_jaw_radius:.3f}", scale=ani.menu_text_scale_small)

        self.menus['table'] = m

        for element in self.menus['table'].elements:
            if element['name'] not in ('Back', ani.options_table):
                element['content'].hide()


    def show_custom_table_options(self, response):
        if response == 'custom':
            for element in self.menus['table'].elements:
                if element['name'] not in ('Back', ani.options_table):
                    element['content'].show()
        else:
            for element in self.menus['table'].elements:
                if element['name'] not in ('Back', ani.options_table):
                    element['content'].hide()


    def populate_ball_options(self):
        m = GenericMenu(title = 'Ball customization')
        m.add_button('Back', lambda: self.show_menu('options'), scale=ani.menu_text_scale)

        m.add_direct_entry(ani.options_ball_diameter, initial=f"{pooltool.R*2:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_friction_roll, initial=f"{pooltool.u_r:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_friction_slide, initial=f"{pooltool.u_s:.3f}", scale=ani.menu_text_scale_small)
        m.add_direct_entry(ani.options_friction_spin, initial=f"{pooltool.u_sp:.3f}", scale=ani.menu_text_scale_small)

        self.menus['balls'] = m


    def show_menu(self, name):
        self.hide_menus()
        self.menus[name].show()

        self.current_menu = self.menus[name]


    def hide_menus(self):
        for menu_name, menu in self.menus.items():
            self.menus[menu_name].hide()

        self.current_menu = None


    def get_menu_options(self):
        """Return an dictionary of user's selected (or default) options"""
        options = {}
        for option in self.menus['options'].elements + self.menus['table'].elements + self.menus['balls'].elements:
            if option['type'] in ('dropdown', 'direct_entry'):
                value = option['content'].get()
                try:
                    value = float(value)
                    if option['convert_factor'] is not None:
                        value *= option['convert_factor']
                except ValueError:
                    pass
                options[option['name']] = value
        return options


class GenericMenu(object):
    def __init__(self, title='', frame_color=(1,1,1,1), title_pos=(0,0,0.8)):
        self.titleMenuBackdrop = DirectFrame(
            frameColor = frame_color,
            frameSize = (-1,1,-1,1),
            parent = render2d,
        )

        self.text_scale = 0.07
        self.move = 0.12

        self.titleMenu = DirectFrame(frameColor = (1,1,1,0))

        self.title = DirectLabel(
            text = title,
            scale = self.text_scale * 1.5,
            pos = title_pos,
            parent = self.titleMenu,
            relief = None,
            text_fg = (0,0,0,1),
        )

        self.next_x, self.next_y = -0.5, 0.6
        self.num_elements = 0
        self.elements = []

        self.hide()


    def get(self, name):
        for element in self.elements:
            if element['name'] == name:
                return element['content']


    def names(self):
        return set([x['name'] for x in self.elements])


    def add_button(self, text, command=None, **kwargs):
        """Add a button at a location based on self.next_x and self.next_y"""

        button = make_button(text, command, **kwargs)
        button.reparentTo(self.titleMenu)
        button.setPos((self.next_x, 0, self.next_y))

        self.elements.append({
            'type': 'button',
            'name': text,
            'content': button,
            'convert_factor': None,
        })

        self.get_next_pos()

        return button


    def add_image(self, path, pos, scale):
        """Add an image to the menu

        Notes
        =====
        - images are parented to self.titleMenuBackdrop (as opposed self.titleMenu) in order to
          preserve their aspect ratios.
        """

        img = OnscreenImage(image=panda_path(path), pos=pos, parent=self.titleMenuBackdrop, scale=scale)
        img.setTransparency(TransparencyAttrib.MAlpha)

        self.elements.append({
            'type': 'image',
            'name': panda_path(path),
            'content': img,
            'convert_factor': None,
        })


    def add_dropdown(self, text, options=['None'], command=None, convert_factor=None, scale=ani.menu_text_scale):

        self.get_next_pos(move=self.move/2)

        dropdown = make_dropdown(text, options, command, scale)
        dropdown.reparentTo(self.titleMenu)
        dropdown.setPos((self.next_x, 0, self.next_y))

        self.elements.append({
            'type': 'dropdown',
            'name': text,
            'content': dropdown,
            'convert_factor': convert_factor,
        })

        self.get_next_pos()


    def add_direct_entry(self, text, command=None, initial="None", convert_factor=None, scale=None):

        self.get_next_pos(move=self.move/2)

        direct_entry = make_direct_entry(text, command, scale, initial)
        direct_entry.reparentTo(self.titleMenu)
        direct_entry.setPos((self.next_x, 0, self.next_y))

        self.elements.append({
            'type': 'direct_entry',
            'name': text,
            'content': direct_entry,
            'convert_factor': convert_factor,
        })

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
        text = text,
        command = command,
        text_align = TextNode.ACenter,
        **kwargs
    )


def make_dropdown(text, options=['None'], command=None, scale=ani.menu_text_scale):
    dropdown = DirectOptionMenu(
        scale=scale,
        items=options,
        highlightColor=(0.65, 0.65, 0.65, 1),
        command=command,
        textMayChange=1,
        text_align = TextNode.ALeft,
    )

    label = DirectLabel(
        text = text + ':',
        relief = None,
        text_fg = (0,0,0,1),
        text_align = TextNode.ALeft,
        parent = dropdown,
        pos = (0, 0, 1),
    )

    return dropdown


def make_direct_entry(text, command=None, scale=ani.menu_text_scale, initial="None"):
    entry = DirectEntry(
        text = "",
        scale = scale,
        command = command,
        initialText = initial,
        numLines = 1,
        width = 4,
        focus = 0,
        focusInCommand = lambda: entry.enterText('')
    )

    label = DirectLabel(
        text = text + ':',
        relief = None,
        text_fg = (0,0,0,1),
        text_align = TextNode.ALeft,
        parent = entry,
        pos = (0, 0, 1.2),
    )

    return entry





















