from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import attrs
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

import pooltool.ani.tasks as tasks
import pooltool.ani.utils as autils
from pooltool.ani.constants import logo_paths, model_dir
from pooltool.ani.fonts import load_font
from pooltool.ani.globals import Global
from pooltool.utils import panda_path
from pooltool.utils.strenum import StrEnum

TEXT_COLOR = (0.1, 0.1, 0.1, 1)
FRAME_COLOR = (0, 0, 0, 1)
TEXT_SCALE = 0.05
BUTTON_TEXT_SCALE = 0.07
AUX_TEXT_SCALE = BUTTON_TEXT_SCALE * 1.0
INPUT_TEXT_SCALE = BUTTON_TEXT_SCALE * 0.6
ERROR_TEXT_SCALE = BUTTON_TEXT_SCALE * 0.6
ERROR_COLOR = (0.9, 0.4, 0.4, 0.8)
INFO_COLOR = (1, 1, 0.9, 0.8)
BACKBUTTON_TEXT_SCALE = 0.06
HEADING_SCALE = 0.12
SUBHEADING_SCALE = 0.08
MOVE = 0.02
INFO_SCALE = 0.025
INFO_TEXT_SCALE = 0.05
MENU_ASSETS = model_dir / "menu"
TITLE_FONT = "LABTSECW"
BUTTON_FONT = "LABTSECW"


class CleanupProtocol(Protocol):
    """Protocol for menu elements that can clean up their Panda3D resources"""

    def cleanup(self) -> None:
        """Clean up any Panda3D objects"""
        ...


@attrs.define
class MenuElementRegistry:
    """Registry for tracking menu elements with type-safe cleanup"""

    elements: list[CleanupProtocol] = attrs.field(factory=list)

    def add(self, element: CleanupProtocol) -> None:
        self.elements.append(element)

    def clear(self) -> None:
        for element in self.elements:
            element.cleanup()
        self.elements.clear()

    def find_focusable_elements(self) -> list[MenuDropdown | MenuCheckbox | MenuInput]:
        """Find elements that can be focused (for click handling)"""
        return [
            e
            for e in self.elements
            if hasattr(e, "dropdown") or hasattr(e, "checkbox") or hasattr(e, "entry")  # type: ignore
        ]


@attrs.define(kw_only=True)
class MenuTitle:
    text: str
    label: DirectLabel

    @classmethod
    def create(cls, text: str, font: str = TITLE_FONT) -> MenuTitle:
        label = DirectLabel(
            text=text,
            scale=HEADING_SCALE,
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=load_font(font),
        )
        return cls(text=text, label=label)

    def cleanup(self) -> None:
        """Clean up the DirectLabel"""
        self.label.removeNode()


@attrs.define(kw_only=True)
class MenuHeader:
    text: str
    label: DirectLabel

    @classmethod
    def create(cls, text: str, font: str = TITLE_FONT) -> MenuHeader:
        label = DirectLabel(
            text=text,
            scale=SUBHEADING_SCALE,
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=load_font(font),
        )
        return cls(text=text, label=label)

    def cleanup(self) -> None:
        """Clean up the DirectLabel"""
        self.label.removeNode()


@attrs.define(kw_only=True)
class MenuButton:
    text: str
    command: Callable[[], None]
    description: str
    button: DirectButton
    info_button: DirectButton | None = None

    @classmethod
    def create(
        cls,
        text: str,
        command: Callable[[], None],
        description: str,
        font: str = BUTTON_FONT,
    ) -> MenuButton:
        button = DirectButton(
            text=text,
            text_align=TextNode.ALeft,
            text_font=load_font(font),
            scale=BUTTON_TEXT_SCALE,
            geom=_load_image_as_plane(MENU_ASSETS / "button.png"),
            relief=None,
            command=command,
        )

        info_button = None
        if description:
            info_button = DirectButton(
                text="",
                text_align=TextNode.ALeft,
                scale=INFO_SCALE,
                image=panda_path(MENU_ASSETS / "info_button.png"),
                relief=None,
            )

        return cls(
            text=text,
            command=command,
            description=description,
            button=button,
            info_button=info_button,
        )

    def cleanup(self) -> None:
        """Clean up the DirectButton and optional info button"""
        self.button.removeNode()
        if self.info_button:
            self.info_button.removeNode()


@attrs.define(kw_only=True)
class MenuBackButton:
    command: Callable[[], None]
    button: DirectButton

    @classmethod
    def create(cls, command: Callable[[], None]) -> MenuBackButton:
        button = DirectButton(
            scale=BACKBUTTON_TEXT_SCALE,
            geom=(
                _load_image_as_plane(MENU_ASSETS / "backbutton.png"),
                _load_image_as_plane(MENU_ASSETS / "backbutton.png"),
                _load_image_as_plane(MENU_ASSETS / "backbutton_hover.png"),
                _load_image_as_plane(MENU_ASSETS / "backbutton.png"),
            ),
            relief=None,
            command=command,
        )
        return cls(command=command, button=button)

    def cleanup(self) -> None:
        """Clean up the DirectButton"""
        self.button.removeNode()


@attrs.define(kw_only=True)
class MenuText:
    text: str
    wrapped_text: str
    label: DirectLabel

    @classmethod
    def create(cls, text: str) -> MenuText:
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

        label = DirectLabel(
            text=wrapped_text,
            scale=TEXT_SCALE,
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=None,
        )

        return cls(text=text, wrapped_text=wrapped_text, label=label)

    def cleanup(self) -> None:
        """Clean up the DirectLabel"""
        self.label.removeNode()


@attrs.define(kw_only=True)
class MenuDropdown:
    name: str
    options: list[str]
    initial_selection: str
    description: str
    command: Callable[[str], None] | None
    title: DirectLabel
    dropdown: DirectOptionMenu
    info_button: DirectButton | None = None

    @classmethod
    def create(
        cls,
        name: str,
        options: list[str],
        initial_selection: str = "",
        description: str = "",
        command: Callable[[str], None] | None = None,
        title_font: str = TITLE_FONT,
        button_font: str = BUTTON_FONT,
    ) -> MenuDropdown:
        # Set initial selection to first option if not provided
        if not initial_selection and options:
            initial_selection = options[0]

        # Create header label
        title = DirectLabel(
            text=name + ":",
            scale=AUX_TEXT_SCALE,
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=load_font(title_font),
        )

        # Create dropdown
        dropdown = DirectOptionMenu(
            scale=BUTTON_TEXT_SCALE * 0.8,
            items=options,
            highlightColor=(0.65, 0.65, 0.65, 1),
            textMayChange=1,
            text_align=TextNode.ALeft,
            text_font=load_font(button_font),
            relief=DGG.RIDGE,
            initialitem=(
                options.index(initial_selection) if initial_selection in options else 0
            ),
            popupMarker_scale=0.6,
            popupMarker_image=_load_image_as_plane(MENU_ASSETS / "dropdown_marker.png"),
            popupMarker_relief=None,
            item_pad=(0.2, 0.2),
            command=command,
        )
        dropdown["frameColor"] = (1, 1, 1, 0.3)

        # Create info button if description provided
        info_button = None
        if description:
            info_button = DirectButton(
                text="",
                text_align=TextNode.ALeft,
                scale=INFO_SCALE,
                image=panda_path(MENU_ASSETS / "info_button.png"),
                relief=None,
            )

        return cls(
            name=name,
            options=options,
            initial_selection=initial_selection,
            description=description,
            command=command,
            title=title,
            dropdown=dropdown,
            info_button=info_button,
        )

    @classmethod
    def from_enum(
        cls,
        name: str,
        enum_class: type[StrEnum],
        initial_selection: StrEnum | None = None,
        description: str = "",
        command: Callable[[str], None] | None = None,
        title_font: str = TITLE_FONT,
        button_font: str = BUTTON_FONT,
    ) -> MenuDropdown:
        """Create a MenuDropdown from a StrEnum class"""
        options = [member.value for member in enum_class]
        initial_selection_str = initial_selection.value if initial_selection else ""

        return cls.create(
            name=name,
            options=options,
            initial_selection=initial_selection_str,
            description=description,
            command=command,
            title_font=title_font,
            button_font=button_font,
        )

    def cleanup(self) -> None:
        """Clean up the DirectLabel, DirectOptionMenu, and optional info button"""
        self.title.removeNode()
        self.dropdown.removeNode()
        if self.info_button:
            self.info_button.removeNode()


@attrs.define(kw_only=True)
class MenuCheckbox:
    name: str
    initial_state: bool
    description: str
    command: Callable[[bool], None] | None
    title: DirectLabel
    checkbox: DirectCheckButton
    info_button: DirectButton | None = None

    @classmethod
    def create(
        cls,
        name: str,
        initial_state: bool = False,
        description: str = "",
        command: Callable[[bool], None] | None = None,
        title_font: str = TITLE_FONT,
        button_font: str = BUTTON_FONT,
    ) -> MenuCheckbox:
        # Create header label
        title = DirectLabel(
            text=name + ":",
            scale=AUX_TEXT_SCALE,
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=load_font(title_font),
        )

        # Create checkbox with wrapped command to convert int to bool
        def wrapped_command(value):
            if command:
                command(bool(value))

        checkbox = DirectCheckButton(
            scale=BUTTON_TEXT_SCALE * 0.8,
            boxBorder=0.05,
            boxPlacement="left",
            text_align=TextNode.ALeft,
            text_font=load_font(button_font),
            relief=DGG.RIDGE,
            frameColor=(1, 1, 1, 0.3),
            command=wrapped_command,
        )

        # Set initial state after creation
        checkbox["indicatorValue"] = int(initial_state)
        checkbox.setIndicatorValue()

        # Create info button if description provided
        info_button = None
        if description:
            info_button = DirectButton(
                text="",
                text_align=TextNode.ALeft,
                scale=INFO_SCALE,
                image=panda_path(MENU_ASSETS / "info_button.png"),
                relief=None,
            )

        return cls(
            name=name,
            initial_state=initial_state,
            description=description,
            command=command,
            title=title,
            checkbox=checkbox,
            info_button=info_button,
        )

    def cleanup(self) -> None:
        """Clean up the DirectLabel, DirectCheckButton, and optional info button"""
        self.title.removeNode()
        self.checkbox.removeNode()
        if self.info_button:
            self.info_button.removeNode()


@attrs.define(kw_only=True)
class MenuInput:
    """Input field.

    Attributes:
        command:
            This function runs when Enter is pressed. Its only argument is the text in
            the input field. Its return value will be used to update the text in the
            input field. The message of any Exceptions raised will be shown to the user
            in the `direct` DirectLabel.
    """

    name: str
    initial_value: str
    description: str
    title: DirectLabel
    message: DirectLabel
    direct_entry: DirectEntry
    info_button: DirectButton | None = None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        initial_value: str = "",
        description: str = "",
        command: Callable[[str], str],
        title_font: str = TITLE_FONT,
        button_font: str = BUTTON_FONT,
        width: float = 15,
    ) -> MenuInput:
        title = DirectLabel(
            text=name + ":",
            scale=AUX_TEXT_SCALE,
            relief=None,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            text_font=load_font(title_font),
        )

        message = DirectLabel(
            frameColor=INFO_COLOR,
            text="Enter to confirm. Esc to cancel.",
            scale=INFO_TEXT_SCALE,
            parent=Global.aspect2d,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            pad=(0.2, 0.2),
        )
        # Set higher render priority for info messages so they appear on top
        message.setBin("gui-popup", 50)

        # Create info button if description is provided
        info_button = None
        if description:
            info_button = DirectButton(
                text="",
                text_align=TextNode.ALeft,
                scale=INFO_SCALE,
                image=panda_path(MENU_ASSETS / "info_button.png"),
                relief=None,
            )

        direct_entry = DirectEntry(
            text="",
            scale=INPUT_TEXT_SCALE,
            width=width,
            relief=DGG.SUNKEN,
            frameColor=(1, 1, 1, 0.7),
            text_fg=TEXT_COLOR,
            text_font=load_font(button_font),
            initialText=initial_value,
            numLines=1,
            focus=0,
            overflow=1,
        )

        input_field = MenuInput(
            name=name,
            initial_value=initial_value,
            description=description,
            title=title,
            message=message,
            direct_entry=direct_entry,
            info_button=info_button,
        )

        def _command(text: str) -> None:
            try:
                cleaned_value = command(text)
            except Exception as e:
                input_field.direct_entry.set(str(input_field.initial_value))
                input_field._show_error_message(str(e))
                return

            if not isinstance(cleaned_value, str):
                raise TypeError(f"{command} must return a string.")

            input_field.direct_entry.set(cleaned_value)
            input_field.initial_value = cleaned_value

        def _unfocus_command():
            if not tasks.has(input_field._task_name):
                message.hide()

        input_field.direct_entry["focusInCommand"] = lambda: message.show()
        input_field.direct_entry["focusOutCommand"] = _unfocus_command
        input_field.direct_entry["command"] = _command

        return input_field

    def _show_error_message(self, error_text: str) -> None:
        """Show error message with red background and auto-hide after 3 seconds"""
        if tasks.has(self._task_name):
            # Error message already is active. Remove it.
            self.message.hide()
            tasks.remove(self._task_name)

        self.message["frameColor"] = ERROR_COLOR
        self.message["text"] = error_text
        self.message.show()

        def hide_error(task):
            self.message.hide()
            self.message["frameColor"] = INFO_COLOR  # Reset to original color
            self.message["text"] = (
                "Enter to confirm. Esc to cancel."  # Reset to original text
            )

        tasks.add_later(3.0, hide_error, self._task_name)

    def cleanup(self) -> None:
        """Clean up the DirectLabel, DirectEntry, and optional info button"""
        tasks.remove(self._task_name)  # Clean up any pending hide task
        self.title.removeNode()
        self.message.removeNode()
        self.direct_entry.removeNode()
        if self.info_button:
            self.info_button.removeNode()

    @property
    def _task_name(self):
        return f"hide-error-message-{self.name}"


def _load_image_as_plane(filepath: Path, yresolution: int = 600) -> NodePath:
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
        self.elements = MenuElementRegistry()
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
            image=panda_path(logo_paths["default"]),
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
        self.elements.clear()
        self.last_element = None

    def add_title(self, menu_title: MenuTitle) -> NodePath:
        title = menu_title.label
        title.reparentTo(self.area.getCanvas())

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
        self.elements.add(menu_title)
        return title_obj

    def add_header(self, menu_header: MenuHeader) -> NodePath:
        header = menu_header.label
        header.reparentTo(self.area.getCanvas())

        if self.last_element:
            autils.alignTo(
                header, self.last_element, autils.CT, autils.CB, gap=(0.5, 0.5)
            )
        else:
            header.setPos((-0.8, 0, 0.8))
        header.setX(-0.8)

        header_x, _, header_z = header.getPos()
        lines = LineSegs()
        lines.setColor(TEXT_COLOR)
        lines.moveTo(header_x, 0, header_z - SUBHEADING_SCALE * 0.15)
        lines.drawTo(0.8, 0, header_z - SUBHEADING_SCALE * 0.15)
        lines.setThickness(1)
        node = lines.create()
        underscore = NodePath(node)
        underscore.reparentTo(self.area.getCanvas())

        # Invisible line for white space
        lines = LineSegs()
        lines.setColor((0, 0, 0, 0))
        lines.moveTo(header_x, 0, header_z - SUBHEADING_SCALE * 0.4)
        lines.drawTo(0.8, 0, header_z - SUBHEADING_SCALE * 0.4)
        lines.setThickness(1)
        node = lines.create()
        whitespace = NodePath(node)
        whitespace.reparentTo(self.area.getCanvas())

        # Create a parent for all the nodes
        header_obj = self.area.getCanvas().attachNewNode(f"header_{self.name}")
        header.reparentTo(header_obj)
        underscore.reparentTo(header_obj)
        whitespace.reparentTo(header_obj)

        self.last_element = header_obj
        self.elements.add(menu_header)
        return header_obj

    def add_button(self, menu_button: MenuButton) -> NodePath:
        button = menu_button.button

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

        # Info button if provided
        info_button_np = None
        if menu_button.info_button:
            info_button = menu_button.info_button
            info_button.bind(
                DGG.ENTER,
                self._display_button_info,
                extraArgs=[menu_button.description],
            )
            info_button.bind(DGG.EXIT, self._destroy_button_info)

            info_button_np = NodePath(info_button)
            info_button_np.reparentTo(self.area.getCanvas())

            autils.alignTo(info_button_np, button_np, autils.CR, autils.CL)
            info_button_np.setX(info_button_np.getX() - 0.02)

        # Create a parent for all the nodes
        button_obj = self.area.getCanvas().attachNewNode(
            f"button_{menu_button.text.replace(' ', '_')}"
        )
        button_np.reparentTo(button_obj)
        if info_button_np:
            info_button_np.reparentTo(button_obj)

        self.last_element = button_np
        self.elements.add(menu_button)
        return button_obj

    def add_back_button(self, menu_back_button: MenuBackButton) -> NodePath:
        button = menu_back_button.button
        button_np = NodePath(button)
        button_np.reparentTo(self.area)
        button_np.setPos(-0.92, 0, 0.22)
        self.elements.add(menu_back_button)
        return button_np

    def add_dropdown(self, menu_dropdown: MenuDropdown) -> NodePath:
        """Add a dropdown menu with the given options"""

        title = menu_dropdown.title
        dropdown = menu_dropdown.dropdown

        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        dropdown_np = NodePath(dropdown)
        dropdown_id = f"dropdown-{self.name}-{menu_dropdown.name.replace(' ', '_')}"
        dropdown_np.setName(dropdown_id)
        dropdown_np.reparentTo(self.area.getCanvas())

        # Position the title
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

        # Info button if provided
        info_button_np = None
        if menu_dropdown.info_button:
            info_button = menu_dropdown.info_button

            # Bind mouse hover to displaying button info
            info_button.bind(
                DGG.ENTER,
                self._display_button_info,
                extraArgs=[menu_dropdown.description],
            )
            info_button.bind(DGG.EXIT, self._destroy_button_info)

            info_button_np = NodePath(info_button)
            info_button_np.reparentTo(self.area.getCanvas())

            # Align the info button next to the title it refers to
            autils.alignTo(info_button_np, title_np, autils.CR, autils.CL)
            # Then shift it over just a bit to give some space
            info_button_np.setX(info_button_np.getX() - 0.02)

        # Create a parent for all the nodes
        dropdown_id = f"dropdown_{menu_dropdown.name.replace(' ', '_')}"
        dropdown_obj = self.area.getCanvas().attachNewNode(dropdown_id)
        title_np.reparentTo(dropdown_obj)
        dropdown_np.reparentTo(dropdown_obj)
        if info_button_np:
            info_button_np.reparentTo(dropdown_obj)

        self.last_element = dropdown_np
        self.elements.add(menu_dropdown)
        return dropdown_obj

    def add_checkbox(self, menu_checkbox: MenuCheckbox) -> NodePath:
        """Add a checkbox with the given configuration"""

        title = menu_checkbox.title
        checkbox = menu_checkbox.checkbox

        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        checkbox_np = NodePath(checkbox)
        checkbox_id = f"checkbox-{self.name}-{menu_checkbox.name.replace(' ', '_')}"
        checkbox_np.setName(checkbox_id)
        checkbox_np.reparentTo(self.area.getCanvas())

        # Position the title
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

        # Info button if provided
        info_button_np = None
        if menu_checkbox.info_button:
            info_button = menu_checkbox.info_button

            # Bind mouse hover to displaying button info
            info_button.bind(
                DGG.ENTER,
                self._display_button_info,
                extraArgs=[menu_checkbox.description],
            )
            info_button.bind(DGG.EXIT, self._destroy_button_info)

            info_button_np = NodePath(info_button)
            info_button_np.reparentTo(self.area.getCanvas())

            # Align the info button next to the title it refers to
            autils.alignTo(info_button_np, title_np, autils.CR, autils.CL)
            # Then shift it over just a bit to give some space
            info_button_np.setX(info_button_np.getX() - 0.02)

        # Create a parent for all the nodes
        checkbox_id = f"checkbox_{menu_checkbox.name.replace(' ', '_')}"
        checkbox_obj = self.area.getCanvas().attachNewNode(checkbox_id)
        title_np.reparentTo(checkbox_obj)
        checkbox_np.reparentTo(checkbox_obj)
        if info_button_np:
            info_button_np.reparentTo(checkbox_obj)

        self.last_element = checkbox_np
        self.elements.add(menu_checkbox)
        return checkbox_obj

    def add_text(self, menu_text: MenuText) -> NodePath:
        text_obj = menu_text.label
        text_obj.reparentTo(self.area.getCanvas())

        if self.last_element:
            autils.alignTo(
                text_obj, self.last_element, autils.CT, autils.CB, gap=(1, 1)
            )
        else:
            text_obj.setPos((-0.7, 0, 0.8))
        text_obj.setX(-0.7)

        self.last_element = text_obj
        self.elements.add(menu_text)
        return text_obj

    def add_input(self, menu_input: MenuInput) -> NodePath:
        """Add a text input field with the given configuration"""

        title = menu_input.title
        message = menu_input.message
        entry = menu_input.direct_entry

        title_np = NodePath(title)
        title_np.reparentTo(self.area.getCanvas())

        message_np = NodePath(message)
        message_np.reparentTo(self.area.getCanvas())
        message_np.hide()

        entry_np = NodePath(entry)
        entry_id = f"input-{self.name}-{menu_input.name.replace(' ', '_')}"
        entry_np.setName(entry_id)
        entry_np.reparentTo(self.area.getCanvas())

        # Position the title
        if self.last_element:
            autils.alignTo(title_np, self.last_element, autils.CT, autils.CB)
        else:
            title_np.setPos(-0.63, 0, 0.8)
        title_np.setX(-0.63)
        title_np.setZ(title_np.getZ() - MOVE)

        # Align the input field to the right of the title title that refers to it.
        autils.alignTo(entry_np, title_np, autils.CL, autils.CR, gap=(0.5, 0.0))

        # Align the message field above the entry.
        autils.alignTo(message_np, entry_np, autils.UL, autils.LL, gap=(0.0, 0.04))

        # Info button if provided
        info_button_np = None
        if menu_input.info_button:
            info_button = menu_input.info_button

            # Bind mouse hover to displaying button info
            info_button.bind(
                DGG.ENTER,
                self._display_button_info,
                extraArgs=[menu_input.description],
            )
            info_button.bind(DGG.EXIT, self._destroy_button_info)

            info_button_np = NodePath(info_button)
            info_button_np.reparentTo(self.area.getCanvas())

            # Align the info button next to the title it refers to
            autils.alignTo(info_button_np, title_np, autils.CR, autils.CL)
            # Then shift it over just a bit to give some space
            info_button_np.setX(info_button_np.getX() - 0.02)

        # Create a parent for all the nodes
        input_id = f"input_{menu_input.name.replace(' ', '_')}"
        input_obj = self.area.getCanvas().attachNewNode(input_id)
        title_np.reparentTo(input_obj)
        entry_np.reparentTo(input_obj)
        if info_button_np:
            info_button_np.reparentTo(input_obj)

        self.last_element = entry_np
        self.elements.add(menu_input)
        return input_obj

    def add_element(self, element: Any):
        if isinstance(element, MenuCheckbox):
            self.add_checkbox(element)
        elif isinstance(element, MenuDropdown):
            self.add_dropdown(element)
        elif isinstance(element, MenuInput):
            self.add_input(element)
        else:
            raise NotImplementedError

    def _highlight_button(self, button: DirectButton, mouse_watcher: Any) -> None:
        self.highlighted_menu_button = button
        self.highlighted_menu_button.setScale(
            self.highlighted_menu_button.getScale() * 11 / 10
        )

    def _unhighlight_button(self, mouse_watcher: Any) -> None:
        if (
            hasattr(self, "highlighted_menu_button")
            and not self.highlighted_menu_button.is_empty()
        ):
            self.highlighted_menu_button.setScale(
                self.highlighted_menu_button.getScale() * 10 / 11
            )

    def _display_button_info(self, msg: str, mouse_watcher: Any) -> None:
        self.hover_msg = DirectLabel(
            frameColor=INFO_COLOR,
            text=msg,
            scale=INFO_TEXT_SCALE,
            parent=Global.aspect2d,
            text_fg=TEXT_COLOR,
            text_align=TextNode.ALeft,
            pad=(0.2, 0.2),
        )
        # Set higher render priority for hover messages so they appear on top
        self.hover_msg.setBin("gui-popup", 50)

        coords = mouse_watcher.getMouse()
        r2d = Point3(coords[0], 0, coords[1])
        a2d = Global.aspect2d.getRelativePoint(Global.render2d, r2d)
        self.hover_msg.setPos(a2d)
        self.hover_msg.setZ(self.hover_msg.getZ() + INFO_SCALE * 2)

    def _destroy_button_info(self, coords: Any) -> None:
        if hasattr(self, "hover_msg"):
            self.hover_msg.removeNode()
