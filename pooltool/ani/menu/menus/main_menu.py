from pooltool.ani.menu._datatypes import BaseMenu, MenuButton, MenuTitle
from pooltool.ani.menu._registry import MenuNavigator


class MainMenu(BaseMenu):
    name: str = "main_menu"

    def __init__(self) -> None:
        super().__init__()

        self.title = MenuTitle.create(
            text="Main Menu",
        )
        self.new_game_button = MenuButton.create(
            text="New Game",
            command=MenuNavigator.go_to_menu("game_setup"),
            description="Play some pool. Shortcut: n",
        )
        self.settings_button = MenuButton.create(
            text="Settings",
            command=MenuNavigator.go_to_menu("settings"),
            description="View and edit available settings.",
        )
        self.quit_button = MenuButton.create(
            text="Quit",
            command=MenuNavigator.quit_application,
            description="Closes pooltool. Shortcut: esc",
        )

    def populate(self) -> None:
        self.add_title(self.title)
        self.add_button(self.new_game_button)
        self.add_button(self.settings_button)
        self.add_button(self.quit_button)
