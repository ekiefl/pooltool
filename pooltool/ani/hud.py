#! /usr/bin/env python

from abc import ABC, abstractmethod
from collections import deque
from typing import List

from direct.gui.OnscreenImage import OnscreenImage
from direct.interval.LerpInterval import LerpFunc
from panda3d.core import CardMaker, NodePath, TextNode, TransparencyAttrib

import pooltool.ani as ani
import pooltool.ani.tasks as tasks
import pooltool.ani.utils as autils
from pooltool.ani.globals import Global
from pooltool.objects.cue.datatypes import Cue
from pooltool.utils import panda_path
from pooltool.utils.strenum import StrEnum, auto


class HUDElement(StrEnum):
    help_text = auto()
    logo = auto()
    log_win = auto()
    english = auto()
    jack = auto()
    power = auto()
    player_stats = auto()


class HUD:
    def __init__(self):
        self.elements = None
        self.initialized = False

    def init(self, hide: List[HUDElement] = list()):
        """Initialize HUD elements and start the HUD update task"""

        self.elements = {
            HUDElement.help_text: Help(),
            HUDElement.logo: Logo(),
            HUDElement.log_win: LogWindow(),
            HUDElement.english: English(),
            HUDElement.jack: Jack(),
            HUDElement.power: Power(),
            HUDElement.player_stats: PlayerStats(),
        }

        for element in self.elements.values():
            element.init()

        for element in hide:
            hud.elements[element].hide()

        self.initialized = True
        tasks.add(self.update_hud, "update_hud")

    def destroy(self):
        if not self.initialized:
            return

        for element in self.elements.values():
            element.destroy()

        self.initialized = False
        tasks.remove("update_hud")

    def toggle_help(self):
        if not self.initialized:
            return
        self.elements[HUDElement.help_text].toggle()

    def update_cue(self, cue: Cue):
        """Update HUD to reflect english, jack, and power of cue

        Returns silently if HUD is not initialized.
        """

        if not self.initialized:
            return

        self.elements[HUDElement.english].set(cue.a, cue.b)
        self.elements[HUDElement.jack].set(cue.theta)
        self.elements[HUDElement.power].set(cue.V0)

    def update_hud(self, task):
        if Global.game is not None:
            self.update_log_window()
            self.update_player_stats()

        if (help_hint := self.elements[HUDElement.help_text].help_hint).is_hidden():
            help_hint.show()

        return task.cont

    def update_player_stats(self):
        self.elements["player_stats"].update(Global.game)
        Global.game.update_player_stats = False

    def update_log_window(self):
        if not Global.game.log.update:
            return

        for msg in Global.game.log.msgs:
            if msg["broadcast"]:
                continue
            if not msg["quiet"]:
                timestamp, msg_txt, sentiment = (
                    msg["elapsed"],
                    msg["msg"],
                    msg["sentiment"],
                )
                self.elements["log_win"].broadcast_msg(
                    f"({timestamp}) {msg_txt}",
                    color=self.elements["log_win"].colors[sentiment],
                )
                msg["broadcast"] = True

        Global.game.log.update = False


class BaseHUDElement(ABC):
    def __init__(self):
        self.dummy_right = NodePath("right_panel_hud")
        self.dummy_right.reparentTo(Global.aspect2d)
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


class Help(BaseHUDElement):
    def __init__(self):
        self.row_num = 0

    def init(self):
        self.destroy()

        self.help_hint = autils.CustomOnscreenText(
            text="Press 'h' to toggle help",
            font_name="LABTSECS",
            pos=(-1.55, 0.93),
            scale=ani.menu_text_scale * 0.9,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            parent=Global.aspect2d,
        )

        self.help_node = Global.aspect2d.attachNewNode("help")

        def add(msg, title=False):
            pos = 0.06 * self.row_num
            text = autils.CustomOnscreenText(
                text=msg,
                style=1,
                fg=(1, 1, 1, 1),
                parent=Global.base.a2dTopLeft,
                align=TextNode.ALeft,
                pos=(-1.45 if not title else -1.55, 0.85 - pos),
                scale=ani.menu_text_scale if title else 0.7 * ani.menu_text_scale,
            )
            text.reparentTo(self.help_node)
            self.row_num += 1

        add("Exit", True)
        add("Leave - [escape]")

        add("Camera controls", True)
        add("Rotate - [mouse]")
        add("Pan - [hold v + mouse]")
        add("Zoom - [hold left-click + mouse]")

        add("Aim controls", True)
        add("Enter aim mode - [a]")
        add("Apply english - [hold e + mouse]")
        add("Elevate cue - [hold b + mouse]")
        add("Precise aiming - [hold f + mouse]")
        add("Raise head - [hold t + mouse]")

        add("Shot controls", True)
        add("Stroke - [hold s] (move mouse down then up)")
        add("Take next shot - [a]")
        add("Undo shot - [z]")
        add("Replay shot - [r]")
        add("Pause shot - [space]")
        add("Rewind - [hold left-arrow] (must be paused)")
        add("Fast forward - [hold right-arrow] (must be paused)")
        add("Slow down - [down-arrow]")
        add("Speed up - [up-arrow]")

        add("Situational controls (not always active)", True)
        add(
            "Call shot - [hold c] (mouse, click to confirm ball, mouse, "
            "click to confirm pocket)"
        )
        add(
            "Move ball - [hold g] (mouse, click confirm ball, mouse, "
            "click to confirm move",
        )
        add(
            "Cue different ball - [hold q] (mouse, click to confirm)",
        )

        self.display = False
        self.help_hint.hide()
        self.help_node.hide()

    def destroy(self):
        if hasattr(self, "help_hint"):
            self.help_hint.hide()
            del self.help_hint

        if hasattr(self, "help_node"):
            self.help_node.hide()
            del self.help_node

    def show(self):
        self.help_hint.show()
        if self.display:
            self.help_node.show()

    def hide(self):
        self.help_node.hide()
        self.help_hint.hide()

    def toggle(self):
        if self.help_node.is_hidden():
            self.help_node.show()
        else:
            self.help_node.hide()


class PlayerStats(BaseHUDElement):
    def __init__(self):
        self.top_spot = -0.18
        self.spacer = 0.05
        self.scale1 = 0.06
        self.scale2 = 0.05
        self.on_screen = []

        self.colors = {
            "inactive": (1, 1, 1, 1),
            "active": (0.5, 1, 0.5, 1),
        }

    def init(self):
        self.destroy()
        self.on_screen = []

    def init_text_object(self, i, msg="", color=None, is_active=False):
        scale = self.scale1 if is_active else self.scale2
        vertical_position = self.top_spot - self.spacer * i

        return autils.CustomOnscreenText(
            text=msg,
            pos=(1.55, vertical_position),
            scale=scale,
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
        players = game.players

        for i, player in enumerate(players):
            msg = f"{player.name}: {game.score[player.name]}"
            is_active = i == game.active_idx
            color = self.colors["active"] if is_active else self.colors["inactive"]
            self.on_screen.append(
                self.init_text_object(i, msg, color=color, is_active=is_active)
            )


class Logo(BaseHUDElement):
    def __init__(self):
        BaseHUDElement.__init__(self)

        self.img = OnscreenImage(
            image=ani.logo_paths["pt_smaller"],
            pos=(0.94, 0, 0.89),
            parent=Global.render2d,
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


class English(BaseHUDElement):
    def __init__(self):
        BaseHUDElement.__init__(self)
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

        self.text = autils.CustomOnscreenText(
            text="(0.000, 0.000)",
            pos=(0, -1.25),
            scale=self.text_scale,
            fg=self.text_color,
            align=TextNode.ACenter,
            mayChange=True,
            parent=self.circle,
        )

    def set(self, a, b):
        self.crosshairs.setPos(-a, 0, b)
        self.text.setText(f"({a:.3f},{b:.3f})")

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


class Power(NodePath, BaseHUDElement):
    """Power meter indicating strength of shot

    Modified from drwr:
    https://discourse.panda3d.org/t/health-bars-using-directgui/2098/3
    """

    def __init__(self, min_strike=0.05, max_strike=7):
        BaseHUDElement.__init__(self)
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
        self.text = autils.CustomOnscreenText(
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

        value = (V0 - ani.min_stroke_speed) / (
            ani.max_stroke_speed - ani.min_stroke_speed
        )
        if value < 0:
            value = 0
        if value > 1:
            value = 1
        self.fg.setScale(value, 1, 1)
        self.bg.setScale(1.0 - value, 1, 1)


class Jack(BaseHUDElement):
    def __init__(self):
        BaseHUDElement.__init__(self)
        self.dir = ani.model_dir / "hud" / "jack"
        self.text_scale = 0.4
        self.text_color = (1, 1, 1, 1)

        self.arc = OnscreenImage(
            image=panda_path(self.dir / "arc.png"),
            pos=(1.4, 0, -0.45),
            parent=Global.aspect2d,
            scale=0.075,
        )
        self.arc.setTransparency(TransparencyAttrib.MAlpha)

        self.cue_cartoon = OnscreenImage(
            image=panda_path(self.dir / "cue.png"),
            parent=Global.aspect2d,
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

        self.text = autils.CustomOnscreenText(
            text="0.00 deg",
            pos=(-1, -1.4),
            scale=self.text_scale,
            fg=self.text_color,
            align=TextNode.ACenter,
            mayChange=True,
            parent=self.arc,
        )

    def set(self, theta):
        self.text.setText(f"{theta:.2f} deg")
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


class LogWindow(BaseHUDElement):
    def __init__(self):
        self.top_spot = -0.95
        self.spacer = 0.05
        self.scale1 = 0.04  # latest message
        self.scale2 = 0.04
        self.on_screen = deque([])

        self.colors = {
            "bad": (0.8, 0.2, 0.2, 1),
            "neutral": (0.4, 0.7, 0.9, 1),
            "good": (0.2, 0.8, 0.2, 1),
        }

    def init(self):
        self.destroy()
        self.on_screen = deque([])
        self.on_screen_max = 10
        for i in range(self.on_screen_max):
            self.on_screen.append(self.init_text_object(i))

    def init_text_object(self, i, msg="", color=None):
        if color is None:
            color = self.colors["neutral"]

        return autils.CustomOnscreenText(
            text=msg,
            pos=(-1.55, self.top_spot + self.spacer * i),
            scale=self.scale1,
            fg=color,
            align=TextNode.ALeft,
            mayChange=True,
        )

    def destroy(self):
        """Delete the on screen text nodes"""
        while self.on_screen:
            on_screen_text = self.on_screen.pop()
            on_screen_text.hide()
            del on_screen_text

    def show(self):
        for on_screen_text in self.on_screen:
            on_screen_text.show()

    def hide(self):
        for on_screen_text in self.on_screen:
            on_screen_text.hide()

    def broadcast_msg(self, msg, color=None):
        if len(self.on_screen) >= self.on_screen_max:
            # Remove the oldest message from the screen
            off_screen = self.on_screen.pop()
            off_screen.hide()
            del off_screen

        # Add the new message to the screen and set its alpha scale to 0 to make it invisible
        new_message = self.init_text_object(0, msg=msg, color=color)
        new_message.setAlphaScale(0)
        self.on_screen.appendleft(new_message)

        # Update positions of existing messages without animating
        for i, on_screen_text in enumerate(self.on_screen):
            on_screen_text.setPos(-1.55, self.top_spot + self.spacer * i)
            if i == 0:
                on_screen_text.setScale(self.scale1)
            else:
                on_screen_text.setScale(self.scale2)

        # Animate the alpha scale of the new message to fade in
        fade_in = LerpFunc(
            new_message.setAlphaScale,
            fromData=0,  # Start the alpha at 0 (completely transparent)
            toData=1,  # End with an alpha of 1 (completely opaque)
            duration=0.6,  # Duration of the fade-in animation
        )
        fade_in.start()


hud = HUD()
