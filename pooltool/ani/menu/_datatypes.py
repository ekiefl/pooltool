from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from direct.gui.DirectGui import (
    DGG,
    DirectButton,
    DirectFrame,
    DirectLabel,
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


def load_image_as_plane(filepath: Path, yresolution: int = 600) -> NodePath:
    tex = Global.loader.loadTexture(panda_path(filepath))
    tex.setBorderColor(Vec4(0, 0, 0, 0))
    tex.setWrapU(Texture.WMBorderColor)
    tex.setWrapV(Texture.WMBorderColor)
    cm = CardMaker(str(filepath) + " card")
    cm.setFrame(
        -tex.getOrigFileXSize(),
        tex.getOrigFileXSize(),
        -tex.getOrigFileYSize(),
        tex.getOrigFileYSize(),
    )
    card = NodePath(cm.generate())
    card.setTexture(tex)
    card.setScale(card.getScale() / yresolution)
    card.flattenLight()
    return card


class BaseMenu(ABC):
    name: str = "_base"

    def __init__(self):
        if self.name == "_base":
            raise NotImplementedError(
                f"{self.__class__.__name__} must declare a `name` class attribute."
            )

        self.title_font = load_font(TITLE_FONT)
        self.button_font = load_font(BUTTON_FONT)

        if self.title_font.get_num_pages() == 0:
            self.title_font.setPixelsPerUnit(90)

        self.last_element: NodePath | None = None
        self.elements: list[dict[str, Any]] = []
        self.hovered_entry: str | None = None

        self._create_backdrop()
        self._create_scrolled_area()

    def _create_backdrop(self) -> None:
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

    def _create_scrolled_area(self) -> None:
        self.area = DirectScrolledFrame(
            frameColor=(1, 1, 1, 0.2),
            canvasSize=(-1, 1, -3, 1),
            frameSize=(-1, 1, -0.9, 0.3),
            scrollBarWidth=0.04,
            horizontalScroll_frameSize=(0, 0, 0, 0),
            parent=Global.aspect2d,
        )
        self.area.setPos(0, 0, 0)
        self.area.setTransparency(TransparencyAttrib.MAlpha)
        self.area.verticalScroll["pageSize"] = 0.05

    @abstractmethod
    def populate(self) -> None:
        pass

    def show(self) -> None:
        self.populate()
        self.area_backdrop.show()
        self.area.show()

    def hide(self) -> None:
        self.area_backdrop.hide()
        self.area.hide()
        self._clear_elements()

    def _clear_elements(self) -> None:
        for element in self.elements:
            if "content" in element and element["content"]:
                element["content"].removeNode()
        self.elements.clear()
        self.last_element = None

    def add_title(self, text: str) -> NodePath:
        title = DirectLabel(
            text=text,
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

        title_x, _, title_z = title.getPos()
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
                "name": text,
                "content": title_obj,
            }
        )

        return title_obj

    def add_button(
        self, text: str, command: Callable[[], None], description: str = ""
    ) -> NodePath:
        button = DirectButton(
            text=text,
            text_align=TextNode.ALeft,
            text_font=self.button_font,
            scale=BUTTON_TEXT_SCALE,
            geom=load_image_as_plane(MENU_ASSETS / "button.png"),
            relief=None,
            command=command,
        )

        # Bind mouse hover to highlighting option
        button.bind(DGG.ENTER, self._highlight_button, extraArgs=[button])
        button.bind(DGG.EXIT, self._unhighlight_button)

        button_np = NodePath(button)
        button_np.reparentTo(self.area.getCanvas())

        if self.last_element:
            autils.alignTo(button_np, self.last_element, autils.CT, autils.CB)
        else:
            button_np.setPos(-0.63, 0, 0.8)
        button_np.setX(-0.63)
        button_np.setZ(button_np.getZ() - MOVE)

        # Info button if description provided
        info_button_np = None
        if description:
            info_button = DirectButton(
                text="",
                text_align=TextNode.ALeft,
                scale=INFO_SCALE,
                image=panda_path(MENU_ASSETS / "info_button.png"),
                relief=None,
            )

            info_button.bind(
                DGG.ENTER, self._display_button_info, extraArgs=[description]
            )
            info_button.bind(DGG.EXIT, self._destroy_button_info)

            info_button_np = NodePath(info_button)
            info_button_np.reparentTo(self.area.getCanvas())

            autils.alignTo(info_button_np, button_np, autils.CR, autils.CL)
            info_button_np.setX(info_button_np.getX() - 0.02)

        # Create a parent for all the nodes
        button_obj = self.area.getCanvas().attachNewNode(
            f"button_{text.replace(' ', '_')}"
        )
        button_np.reparentTo(button_obj)
        if info_button_np:
            info_button_np.reparentTo(button_obj)

        self.last_element = button_np

        self.elements.append(
            {
                "type": "button",
                "name": text,
                "content": button_obj,
                "object": button,
            }
        )

        return button_obj

    def add_back_button(self, command: Callable[[], None]) -> NodePath:
        button = DirectButton(
            scale=BACKBUTTON_TEXT_SCALE,
            geom=(
                load_image_as_plane(MENU_ASSETS / "backbutton.png"),
                load_image_as_plane(MENU_ASSETS / "backbutton.png"),
                load_image_as_plane(MENU_ASSETS / "backbutton_hover.png"),
                load_image_as_plane(MENU_ASSETS / "backbutton.png"),
            ),
            relief=None,
            command=command,
        )

        button_np = NodePath(button)
        button_np.reparentTo(self.area)
        button_np.setPos(-0.92, 0, 0.22)

        self.elements.append(
            {
                "type": "backbutton",
                "content": button_np,
                "object": button,
            }
        )

        return button_np

    def add_text(self, text: str) -> NodePath:
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
        wrapped_text = "\n".join(new_text)

        text_obj = DirectLabel(
            text=wrapped_text,
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
                "name": "",
                "text": wrapped_text,
                "content": text_obj,
            }
        )

        return text_obj

    def _highlight_button(self, button: DirectButton, mouse_watcher: Any) -> None:
        self.highlighted_menu_button = button
        self.highlighted_menu_button.setScale(
            self.highlighted_menu_button.getScale() * 11 / 10
        )

    def _unhighlight_button(self, mouse_watcher: Any) -> None:
        if hasattr(self, "highlighted_menu_button"):
            self.highlighted_menu_button.setScale(
                self.highlighted_menu_button.getScale() * 10 / 11
            )

    def _display_button_info(self, msg: str, mouse_watcher: Any) -> None:
        self.hover_msg = DirectLabel(
            frameColor=(1, 1, 0.9, 1),
            text=msg,
            scale=INFO_TEXT_SCALE,
            parent=Global.aspect2d,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            pad=(0.2, 0.2),
        )

        coords = mouse_watcher.getMouse()
        r2d = Point3(coords[0], 0, coords[1])
        a2d = Global.aspect2d.getRelativePoint(Global.render2d, r2d)
        self.hover_msg.setPos(a2d)
        self.hover_msg.setZ(self.hover_msg.getZ() + INFO_SCALE * 2)

    def _destroy_button_info(self, coords: Any) -> None:
        if hasattr(self, "hover_msg"):
            self.hover_msg.removeNode()
