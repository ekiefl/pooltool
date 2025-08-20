from pooltool.ani.menu._datatypes import BaseMenu, MenuBackButton, MenuText, MenuTitle
from pooltool.ani.menu._registry import MenuNavigator


class SettingsMenu(BaseMenu):
    name: str = "settings"

    def __init__(self) -> None:
        super().__init__()

        self.title = MenuTitle.create(text="Settings")
        self.back_button = MenuBackButton.create(MenuNavigator.go_to_menu("main_menu"))
        self.text = MenuText.create("Coming soon...")

    def populate(self) -> None:
        self.add_back_button(self.back_button)
        self.add_title(self.title)
        self.add_text(self.text)
