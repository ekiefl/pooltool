from pooltool.ani.menu._datatypes import BaseMenu, MenuBackButton, MenuTitle
from pooltool.ani.menu._factory import create_elements_from_dataclass
from pooltool.ani.menu._registry import MenuNavigator
from pooltool.config import settings


class SettingsMenu(BaseMenu):
    name: str = "settings"

    def __init__(self) -> None:
        super().__init__()

        self.title = MenuTitle.create(text="Settings")
        self.back_button = MenuBackButton.create(MenuNavigator.go_to_menu("main_menu"))

    def populate(self) -> None:
        self.add_back_button(self.back_button)

        self.add_title(self.title)

        self.add_title(MenuTitle.create(text="Graphics"))
        for element in create_elements_from_dataclass(settings.graphics):
            self.add_element(element)
