from pooltool.ani.menu._registry import MenuNavigator, MenuRegistry
from pooltool.ani.menu.game_setup import GameSetupMenu
from pooltool.ani.menu.main_menu import MainMenu
from pooltool.ani.menu.settings import SettingsMenu

MenuRegistry.register(GameSetupMenu)
MenuRegistry.register(MainMenu)
MenuRegistry.register(SettingsMenu)

__all__ = [
    "MenuRegistry",
    "MenuNavigator",
]
