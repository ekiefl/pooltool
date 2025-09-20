from collections.abc import Callable

from pooltool.ani.globals import Global
from pooltool.ani.menu._datatypes import BaseMenu, MenuBackButton, MenuHeader, MenuTitle
from pooltool.ani.menu._factory import create_elements_from_dataclass
from pooltool.ani.menu._registry import MenuNavigator
from pooltool.config import settings


def _fps_wrap(func: Callable[[str], None]) -> Callable[[str], None]:
    def inner(value: str) -> None:
        if int(float(value)) < 5:
            value = "5"

        func(value)
        Global.clock.setFrameRate(settings.graphics.fps)

    return inner


class SettingsMenu(BaseMenu):
    name: str = "settings"

    def __init__(self) -> None:
        super().__init__()

        self.title = MenuTitle.create(text="Settings")
        self.back_button = MenuBackButton.create(MenuNavigator.go_to_menu("main_menu"))

    def populate(self) -> None:
        self.add_back_button(self.back_button)
        self.add_title(self.title)

        self.add_header(MenuHeader.create(text="Graphics"))
        for element, field in create_elements_from_dataclass(settings.graphics):
            if field.name == "fps":
                # Patch the FPS function
                entry = element.direct_entry
                entry["command"] = _fps_wrap(entry["command"])

            self.add_element(element)
