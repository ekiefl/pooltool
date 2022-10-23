#! /usr/bin/env python

from abc import ABC, abstractmethod
from collections import deque

from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from direct.interval.IntervalGlobal import (
    LerpFunctionInterval,
    Parallel,
    Sequence,
    Wait,
)
from panda3d.core import CardMaker, NodePath, TextNode, TransparencyAttrib

import pooltool.ani as ani
import pooltool.ani.utils as autils
from pooltool.utils import panda_path


class HUD:
    def __init__(self):
        self.game = None

    def attach_game(self, game):
        self.game = game

    def init_hud(self):
        """Initialize HUD elements and return HUD update task"""

        self.hud_elements = {
            "logo": Logo(),
            "log_win": LogWindow(),
            "english": English(),
            "jack": Jack(),
            "power": Power(),
            "player_stats": PlayerStats(),
        }

        for element in self.hud_elements.values():
            element.init()

        return self.update_hud

    def destroy_hud(self):
        for element in self.hud_elements.values():
            element.destroy()

    def hide_hud_element(self, element):
        assert element in self.hud_elements
        self.hud_elements["element"].hide()

    def show_hud_element(self, element):
        assert element in self.hud_elements
        self.hud_elements["element"].show()

    def update_hud(self, task):
        if self.game:
            self.update_log_window()
            self.update_player_stats()

        return task.cont

    def update_player_stats(self):
        if not self.game.update_player_stats:
            return

        self.hud_elements["player_stats"].update(self.game)
        self.game.update_player_stats = False

    def update_log_window(self):
        if not self.game.log.update:
            return

        for msg in reversed(self.game.log.msgs):
            if not msg["quiet"]:
                if not msg["broadcast"]:
                    timestamp, msg_txt, sentiment = (
                        msg["elapsed"],
                        msg["msg"],
                        msg["sentiment"],
                    )
                    self.hud_elements["log_win"].broadcast_msg(
                        f"({timestamp}) {msg_txt}",
                        color=self.hud_elements["log_win"].colors[sentiment],
                    )
                    msg["broadcast"] = True
                else:
                    break

        self.game.log.update = False


hud = HUD()


class HUDElement(ABC):
    def __init__(self):
        # Panda pollutes the global namespace, appease linters
        self.aspect2d = __builtins__["aspect2d"]
        self.render2d = __builtins__["render2d"]

        self.dummy_right = NodePath("right_panel_hud")
        self.dummy_right.reparentTo(self.aspect2d)
        self.dummy_right.setPos(1.25, 0, 0)

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


class PlayerStats(HUDElement):
    def __init__(self):
        self.top_spot = -0.18
        self.spacer = 0.05
        self.scale1 = 0.06
        self.scale2 = 0.04
        self.on_screen = []

        self.colors = {
            "inactive": (1, 1, 1, 1),
            "active": (0.5, 1, 0.5, 1),
        }

    def init(self):
        self.destroy()
        self.on_screen = []

    def init_text_object(self, i, msg="", color=None):
        if color is None:
            color = self.colors["inactive"]

        return OnscreenText(
            text=msg,
            pos=(1.55, self.top_spot + self.spacer * i),
            scale=self.scale1 if i == 0 else self.scale2,
            fg=color,
            align=TextNode.ARight,
            mayChange=True,
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

    def update(self, game):
        self.init()

        for i, player in enumerate(game.player_order()):
            msg = f"{player.name}: {player.points}"
            color = self.colors["active"] if i == 0 else self.colors["inactive"]
            self.on_screen.append(self.init_text_object(i, msg, color=color))


class Logo(HUDElement):
    def __init__(self):
        HUDElement.__init__(self)

        self.img = OnscreenImage(
            image=ani.logo_paths["pt_smaller"],
            pos=(0.94, 0, 0.89),
            parent=self.render2d,
            scale=(0.08 * 0.49, 1, 0.08),
        )
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
        HUDElement.__init__(self)
        self.dir = ani.model_dir / "hud" / "english"
        self.text_scale = 0.2
        self.text_color = (1, 1, 1, 1)

        self.circle = OnscreenImage(
            image=panda_path(self.dir / "circle.png"),
            parent=self.dummy_right,
            scale=0.15,
        )
        self.circle.setTransparency(TransparencyAttrib.MAlpha)
        autils.alignTo(self.circle, self.dummy_right, autils.CL, autils.C)
        self.circle.setZ(-0.65)

        self.crosshairs = OnscreenImage(
            image=panda_path(self.dir / "crosshairs.png"),
            pos=(0, 0, 0),
            parent=self.circle,
            scale=0.14,
        )
        self.crosshairs.setTransparency(TransparencyAttrib.MAlpha)

        self.text = OnscreenText(
            text="(0.00, 0.00)",
            pos=(0, -1.15),
            scale=self.text_scale,
            fg=self.text_color,
            align=TextNode.ACenter,
            mayChange=True,
            parent=self.circle,
        )

    def set(self, a, b):
        self.crosshairs.setPos(-a, 0, b)
        self.text.setText(f"({a:.2f},{b:.2f})")

    def init(self):
        self.show()

    def show(self):
        self.circle.show()

    def hide(self):
        self.circle.hide()

    def destroy(self):
        self.hide()
        del self.text
        del self.crosshairs
        del self.circle


class Power(NodePath, HUDElement):
    """Power meter indicating strength of shot

    Modified from drwr:
    https://discourse.panda3d.org/t/health-bars-using-directgui/2098/3
    """

    def __init__(self, min_strike=0.05, max_strike=7):
        self.min_strike = min_strike
        self.max_strike = max_strike

        HUDElement.__init__(self)
        self.text_scale = 0.11
        self.text_color = (1, 1, 1, 1)

        NodePath.__init__(self, "powerbar")
        self.reparentTo(self.dummy_right)

        cmfg = CardMaker("fg")
        cmfg.setFrame(0, 1, -0.04, 0.04)
        self.fg = self.attachNewNode(cmfg.generate())

        cmbg = CardMaker("bg")
        cmbg.setFrame(-1, 0, -0.04, 0.04)
        self.bg = self.attachNewNode(cmbg.generate())
        self.bg.setPos(1, 0, 0)

        self.fg.setColor(1, 0, 0, 1)
        self.bg.setColor(0.5, 0.5, 0.5, 1)

        self.setScale(0.3)

        start_value = 2
        self.text = OnscreenText(
            text=f"{start_value:.2f} m/s",
            pos=(0, 0),
            scale=self.text_scale,
            fg=self.text_color,
            align=TextNode.ACenter,
            mayChange=True,
            parent=self,
        )
        self.text.setPos(0.5, -0.15)
        self.setPos(0, 0, -0.9)

        self.set(start_value)

    def init(self):
        self.show()

    def destroy(self):
        self.hide()
        del self.text
        del self

    def set(self, V0):
        self.text.setText(f"{V0:.2f} m/s")

        value = (V0 - self.min_strike) / (self.max_strike - self.min_strike)
        if value < 0:
            value = 0
        if value > 1:
            value = 1
        self.fg.setScale(value, 1, 1)
        self.bg.setScale(1.0 - value, 1, 1)


class Jack(HUDElement):
    def __init__(self):
        HUDElement.__init__(self)
        self.dir = ani.model_dir / "hud" / "jack"
        self.text_scale = 0.4
        self.text_color = (1, 1, 1, 1)

        self.arc = OnscreenImage(
            image=panda_path(self.dir / "arc.png"),
            pos=(1.4, 0, -0.45),
            parent=self.aspect2d,
            scale=0.075,
        )
        self.arc.setTransparency(TransparencyAttrib.MAlpha)

        self.cue_cartoon = OnscreenImage(
            image=panda_path(self.dir / "cue.png"),
            parent=self.aspect2d,
            pos=(0, 0, 0),
            scale=(0.15, 1, 0.01),
        )
        self.cue_cartoon.setTransparency(TransparencyAttrib.MAlpha)
        autils.alignTo(self.cue_cartoon, self.dummy_right, autils.CL, autils.C)
        self.cue_cartoon.setZ(-0.40)

        autils.alignTo(self.arc, self.cue_cartoon, autils.LR, autils.CR)

        self.rotational_point = OnscreenImage(
            image=panda_path(ani.model_dir / "hud" / "english" / "circle.png"),
            parent=self.arc,
            scale=0.15,
        )
        self.rotational_point.setTransparency(TransparencyAttrib.MAlpha)
        autils.alignTo(self.rotational_point, self.arc, autils.C, autils.LR)

        self.cue_cartoon.wrtReparentTo(self.rotational_point)

        self.text = OnscreenText(
            text="0 deg",
            pos=(-1, -1.4),
            scale=self.text_scale,
            fg=self.text_color,
            align=TextNode.ACenter,
            mayChange=True,
            parent=self.arc,
        )

    def set(self, theta):
        self.text.setText(f"{theta:.1f} deg")
        self.rotational_point.setR(theta)

    def init(self):
        self.show()

    def show(self):
        self.arc.show()
        self.cue_cartoon.show()

    def hide(self):
        self.arc.hide()
        self.cue_cartoon.hide()

    def destroy(self):
        self.hide()
        del self.arc


class LogWindow(HUDElement):
    def __init__(self):
        self.top_spot = -0.95
        self.spacer = 0.05
        self.scale1 = 0.05
        self.scale2 = 0.04
        self.on_screen = deque([])

        self.colors = {
            "bad": (1, 0.5, 0.5, 1),
            "neutral": (1, 1, 0.5, 1),
            "good": (0.5, 1, 0.5, 1),
        }

    def init(self):
        self.destroy()
        self.on_screen = deque([])
        self.on_screen_max = 5
        for i in range(self.on_screen_max):
            self.on_screen.append(self.init_text_object(i))

    def init_text_object(self, i, msg="", color=None):
        if color is None:
            color = self.colors["neutral"]

        return OnscreenText(
            text=msg,
            pos=(-1.55, self.top_spot + self.spacer * i),
            scale=self.scale1,
            fg=color,
            align=TextNode.ALeft,
            mayChange=True,
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
            start, stop = (
                self.top_spot + self.spacer * (i - 1),
                self.top_spot + self.spacer * i,
            )
            sequence = Sequence(
                Wait(0.2),
                LerpFunctionInterval(
                    on_screen_text.setY, toData=stop, fromData=start, duration=0.5
                ),
            )
            if i == 0:
                sequence = Parallel(
                    LerpFunctionInterval(
                        on_screen_text.setScale,
                        toData=self.scale1,
                        fromData=self.scale2,
                        duration=0.5,
                    ),
                    sequence,
                    LerpFunctionInterval(
                        on_screen_text.setAlphaScale, toData=1, fromData=0, duration=0.5
                    ),
                )
            elif i == 1:
                sequence = Parallel(
                    sequence,
                    LerpFunctionInterval(
                        on_screen_text.setScale,
                        toData=self.scale2,
                        fromData=self.scale1,
                        duration=0.5,
                    ),
                    LerpFunctionInterval(
                        on_screen_text.setAlphaScale,
                        toData=1,
                        fromData=0.7,
                        duration=0.5,
                    ),
                )
            elif i == self.on_screen_max - 1:
                sequence = Parallel(
                    sequence,
                    LerpFunctionInterval(
                        on_screen_text.setAlphaScale, toData=0, fromData=1, duration=0.5
                    ),
                )
            animation.append(sequence)
        animation.start()
