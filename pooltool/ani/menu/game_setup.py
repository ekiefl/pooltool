from pooltool.ani.menu._datatypes import BaseMenu
from pooltool.ani.menu._registry import MenuNavigator


class GameSetupMenu(BaseMenu):
    name: str = "game_setup"

    def populate(self) -> None:
        self.add_title("Game Setup")

        self.add_back_button(MenuNavigator.go_to_menu("main_menu"))

        self.add_button(
            "Play now",
            MenuNavigator.enter_game,
            "Enter the game with the currently selected settings",
        )

        self.add_text(
            "There used to be some customizable options here, but due to some dramatic "
            "changes to the codebase, the archaic menu system no longer plugs into the "
            "backend. That will change one day, but today is not that day :( For now, just "
            'click "Play now"'
        )
