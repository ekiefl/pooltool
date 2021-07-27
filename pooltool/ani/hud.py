#! /usr/bin/env python

from collections import deque
from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.gui.OnscreenText import OnscreenText

class HUD(object):
    def __init__(self):
        self.logo = Logo()
        self.log_win = LogWindow()


    def init_hud(self):
        self.log_win.init()
        self.add_task(self.update_hud, 'update_hud')


    def delete_hud(self):
        self.remove_task('update_hud')

        # remove log messages
        self.log_win.clear()


    def update_log_window(self):
        if not self.game.log.update:
            return

        for msg in reversed(self.game.log.msgs):
            if not msg['quiet']:
                if not msg['broadcast']:
                    timestamp, msg_txt, sentiment = msg['elapsed'], msg['msg'], msg['sentiment']
                    self.log_win.broadcast_msg(f"({timestamp}) {msg_txt}", color=self.log_win.colors[sentiment])
                    msg['broadcast'] = True
                else:
                    break

        self.game.log.update = False


    def update_hud(self, task):
        self.update_log_window()

        return task.cont


class Logo(object):
    def __init__(self):
        self.logo = OnscreenText(
            text='pooltool',
            style=1,
            fg=(1, 1, 0, 1),
            shadow=(0, 0, 0, 0.5),
            pos=(0.87, -0.95),
            scale = 0.07,
        )


class LogWindow(object):
    def __init__(self):
        self.top_spot = -0.9
        self.spacer = 0.05
        self.scale1 = 0.05
        self.scale2 = 0.04

        self.colors = {
            'bad': (1, 0.5, 0.5, 1),
            'neutral': (1, 1, 0.5, 1),
            'good': (0.5, 1, 0.5, 1),
        }


    def init(self):
        self.on_screen = deque([])
        self.on_screen_max = 5
        for i in range(self.on_screen_max):
            self.on_screen.append(self.init_text_object(i))


    def init_text_object(self, i, msg="", color=None):
        if color is None:
            color = self.colors['neutral']

        return OnscreenText(
            text=msg,
            pos=(-1.5, self.top_spot+self.spacer*i),
            scale=self.scale1,
            fg=color,
            align=TextNode.ALeft,
            mayChange=True
        )


    def delete(self):
        """Delete the on screen text nodes"""
        while True:
            try:
                on_screen_text = self.on_screen.pop()
                on_screen_text.hide()
                del on_screen_text
            except IndexError:
                break


    def clear(self):
        """Delete then reinitialize the on screen text nodes"""
        self.delete()
        self.init()


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


