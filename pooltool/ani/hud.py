#! /usr/bin/env python

import pooltool

from pooltool.ani import logo_paths

from abc import ABC, abstractmethod
from pathlib import Path
from collections import deque
from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage

class HUD(object):
    def __init__(self):
        pass


    def init_hud(self):
        self.hud_elements = {
            'logo': Logo(),
            'log_win': LogWindow(),
            'english': English(),
        }

        for element in self.hud_elements.values():
            element.init()

        self.add_task(self.update_hud, 'update_hud')


    def destroy_hud(self):
        self.remove_task('update_hud')

        # remove log messages
        for element in self.hud_elements.values():
            element.destroy()


    def hide_hud_element(self, element):
        assert element in self.hud_elements
        self.hud_elements['element'].hide()


    def show_hud_element(self, element):
        assert element in self.hud_elements
        self.hud_elements['element'].show()


    def update_log_window(self):
        if not self.game.log.update:
            return

        for msg in reversed(self.game.log.msgs):
            if not msg['quiet']:
                if not msg['broadcast']:
                    timestamp, msg_txt, sentiment = msg['elapsed'], msg['msg'], msg['sentiment']
                    self.hud_elements['log_win'].broadcast_msg(f"({timestamp}) {msg_txt}", color=self.hud_elements['log_win'].colors[sentiment])
                    msg['broadcast'] = True
                else:
                    break

        self.game.log.update = False


    def update_hud(self, task):
        self.update_log_window()

        return task.cont


class HUDElement(ABC):
    @abstractmethod
    def init(self):
        pass


    @abstractmethod
    def show(self):
        pass


    @abstractmethod
    def hide(self):
        pass


    @abstractmethod
    def destroy(self):
        pass


class Logo(HUDElement):
    def __init__(self):
        self.img = OnscreenImage(image=logo_paths['smaller'], pos=(0.85, 0, 0.85), parent=render2d, scale=0.10)
        self.img.setTransparency(TransparencyAttrib.MAlpha)


    def init(self):
        self.show()


    def show(self):
        self.img.show()


    def hide(self):
        self.img.hide()


    def destroy(self):
        self.hide()
        del self.img


class English(HUDElement):
    def __init__(self):
        self.dir = Path(pooltool.__file__).parent.parent / 'models' / 'hud' / 'english'

        self.circle = OnscreenImage(
            image=str(self.dir / 'circle.png'),
            pos=(1.4, 0, -0.8),
            parent=aspect2d,
            scale=0.15
        )
        self.circle.setTransparency(TransparencyAttrib.MAlpha)

        self.crosshairs = OnscreenImage(
            image=str(self.dir / 'crosshairs.png'),
            pos=(0, 0, 0),
            parent=self.circle,
            scale=0.14
        )
        self.crosshairs.setTransparency(TransparencyAttrib.MAlpha)


    def init(self):
        self.show()


    def show(self):
        self.circle.show()


    def hide(self):
        self.circle.hide()


    def destroy(self):
        self.hide()
        del self.circle


class LogWindow(HUDElement):
    def __init__(self):
        self.top_spot = -0.95
        self.spacer = 0.05
        self.scale1 = 0.05
        self.scale2 = 0.04
        self.on_screen = deque([])

        self.colors = {
            'bad': (1, 0.5, 0.5, 1),
            'neutral': (1, 1, 0.5, 1),
            'good': (0.5, 1, 0.5, 1),
        }


    def init(self):
        self.destroy()
        self.on_screen = deque([])
        self.on_screen_max = 5
        for i in range(self.on_screen_max):
            self.on_screen.append(self.init_text_object(i))


    def init_text_object(self, i, msg="", color=None):
        if color is None:
            color = self.colors['neutral']

        return OnscreenText(
            text=msg,
            pos=(-1.55, self.top_spot+self.spacer*i),
            scale=self.scale1,
            fg=color,
            align=TextNode.ALeft,
            mayChange=True
        )


    def destroy(self):
        """Delete the on screen text nodes"""
        while True:
            try:
                on_screen_text = self.on_screen.pop()
                on_screen_text.hide()
                del on_screen_text
            except IndexError:
                break


    def show(self):
        for on_screen_text in self.on_screen:
            on_screen_text.show()


    def hide(self):
        for on_screen_text in self.on_screen:
            on_screen_text.hide()


    def broadcast_msg(self, msg, color=None):
        self.on_screen.appendleft(self.init_text_object(-1, msg=msg, color=color))

        off_screen = self.on_screen.pop()
        off_screen.hide()
        del off_screen

        animation = Parallel()
        for i, on_screen_text in enumerate(self.on_screen):
            start, stop = self.top_spot+self.spacer*(i-1), self.top_spot+self.spacer*i
            sequence = Sequence(
                Wait(0.2),
                LerpFunctionInterval(on_screen_text.setY, toData=stop, fromData=start, duration=0.5),
            )
            if i == 0:
                sequence = Parallel(
                    LerpFunctionInterval(on_screen_text.setScale, toData=self.scale1, fromData=self.scale2, duration=0.5),
                    sequence,
                    LerpFunctionInterval(on_screen_text.setAlphaScale, toData=1, fromData=0, duration=0.5),
                )
            elif i == 1:
                sequence = Parallel(
                    sequence,
                    LerpFunctionInterval(on_screen_text.setScale, toData=self.scale2, fromData=self.scale1, duration=0.5),
                    LerpFunctionInterval(on_screen_text.setAlphaScale, toData=1, fromData=0.7, duration=0.5),
                )
            elif i == self.on_screen_max - 1:
                sequence = Parallel(
                    sequence,
                    LerpFunctionInterval(on_screen_text.setAlphaScale, toData=0, fromData=1, duration=0.5
                    ),
                )
            animation.append(sequence)
        animation.start()


