from pooltool.ani.menu._datatypes import BaseMenu
from pooltool.ani.menu._registry import MenuNavigator


class MainMenu(BaseMenu):
    name: str = "main_menu"

    def populate(self) -> None:
        self.add_title("Main Menu")

        self.add_button(
            "New Game",
            MenuNavigator.go_to_menu("game_setup"),
            "Play some pool. Shortcut: n",
        )

        self.add_button(
            "Settings",
            MenuNavigator.go_to_menu("settings"),
            "View and edit available settings.",
        )

        self.add_button(
            "Quit", MenuNavigator.quit_application, "Closes pooltool. Shortcut: esc"
        )
