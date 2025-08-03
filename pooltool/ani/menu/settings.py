from pooltool.ani.menu._datatypes import BaseMenu
from pooltool.ani.menu._registry import MenuNavigator


class SettingsMenu(BaseMenu):
    name: str = "settings"

    def populate(self) -> None:
        self.add_title("Settings")

        self.add_back_button(MenuNavigator.go_to_menu("main_menu"))

        self.add_text("On the horizon, but don't hold your breath...")
