from pooltool.ani.menu._registry import MenuNavigator, MenuRegistry
from pooltool.ani.menu.menus.game_setup import GameSetupMenu
from pooltool.ani.menu.menus.main_menu import MainMenu
from pooltool.ani.menu.menus.settings import SettingsMenu

MenuRegistry.register(GameSetupMenu)
MenuRegistry.register(MainMenu)
MenuRegistry.register(SettingsMenu)

__all__ = [
    "MenuRegistry",
    "MenuNavigator",
]
