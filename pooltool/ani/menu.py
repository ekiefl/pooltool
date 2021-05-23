#! /usr/bin/env python

import pooltool.ani as ani

import sys

from panda3d.core import *
from direct.gui.DirectGui import *


class MenuManager(object):
    def __init__(self):

        self.menus = {}
        self.populate_main()
        self.populate_options()

        self.current_menu = None


    def populate_main(self):
        m = GenericMenu(title = 'Main Screen')
        m.add_button('New Game', self.go)
        m.add_button('Options', lambda: self.show_menu('options'))
        m.add_button('Quit', sys.exit)

        self.menus['main'] = m


    def populate_options(self):
        m = GenericMenu(title = 'Options')
        m.add_button('Back', lambda: self.show_menu('main'))
        m.add_dropdown('Arrangement', options=['9_break', '10_balls'])
        m.add_direct_entry('Enter weight')

        self.menus['options'] = m


    def show_menu(self, name):
        self.hide_menus()
        self.menus[name].show()

        self.current_menu = self.menus[name]


    def hide_menus(self):
        for menu_name, menu in self.menus.items():
            self.menus[menu_name].hide()

        self.current_menu = None


class GenericMenu(object):
    def __init__(self, title='', frame_color=(0,0,0,1), title_pos=(0,0,0.8)):
        self.titleMenuBackdrop = DirectFrame(
            frameColor = frame_color,
            frameSize = (-1,1,-1,1),
            parent = render2d,
        )

        self.logo = OnscreenText(
            text='pooltool',
            style=1,
            fg=(1, 1, 0, 1),
            shadow=(0, 0, 0, 0.5),
            pos=(0.87, -0.95),
            scale = 0.07,
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
            text_fg = (1,1,1,1),
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


    def add_button(self, text, command=None):
        """Add a button at a location based on self.next_x and self.next_y"""

        button = make_button(text, command)
        button.reparentTo(self.titleMenu)
        button.setPos((self.next_x, 0, self.next_y))

        self.elements.append({
            'type': 'button',
            'name': text,
            'content': button,
        })

        self.get_next_pos()


    def add_dropdown(self, text, options=['None'], command=None):

        self.get_next_pos(move=self.move/2)

        dropdown = make_dropdown(text, options, command)
        dropdown.reparentTo(self.titleMenu)
        dropdown.setPos((self.next_x, 0, self.next_y))

        self.elements.append({
            'type': 'dropdown',
            'name': text,
            'content': dropdown,
        })

        self.get_next_pos()


    def add_direct_entry(self, text, command=None, initial="None"):

        self.get_next_pos(move=self.move/2)

        direct_entry = make_direct_entry(text, command, initial)
        direct_entry.reparentTo(self.titleMenu)
        direct_entry.setPos((self.next_x, 0, self.next_y))

        self.elements.append({
            'type': 'direct_entry',
            'name': text,
            'content': direct_entry,
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


def make_button(text, command=None):
    return DirectButton(
        text = text,
        command = command,
        scale = ani.menu_text_scale,
        text_align = TextNode.ALeft,
    )


def make_dropdown(text, options=['None'], command=None):
    dropdown = DirectOptionMenu(
        scale=ani.menu_text_scale,
        items=options,
        highlightColor=(0.65, 0.65, 0.65, 1),
        command=command,
        textMayChange=1,
        text_align = TextNode.ALeft,
    )

    label = DirectLabel(
        text = text + ':',
        relief = None,
        text_fg = (1,1,1,1),
        text_align = TextNode.ALeft,
        parent = dropdown,
        pos = (0, 0, 1),
    )

    return dropdown


def make_direct_entry(text, command=None, initial="None"):

    entry = DirectEntry(
        text = "",
        scale = ani.menu_text_scale,
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
        text_fg = (1,1,1,1),
        text_align = TextNode.ALeft,
        parent = entry,
        pos = (0, 0, 1.2),
    )

    return entry





















