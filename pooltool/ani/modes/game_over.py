#! /usr/bin/env python

from direct.gui.DirectGui import OnscreenText

from pooltool.ani.action import Action
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode


class GameOverMode(BaseMode):
    name = Mode.game_over
    col_spacing = 0.25
    row_spacing = 0.04
    stat_font_size = 0.04
    left_most = -0.33
    top_most = 0.4
    keymap = {
        Action.quit: False,
    }

    def enter(self):
        self.mouse.show()
        self.mouse.absolute()

        self.task_action("escape", Action.quit, True)
        self.render_game_over_screen()

    def exit(self):
        self.game_over_menu.hide()
        for text in self.text.values():
            text.hide()

        del self.game_over_menu
        del self.text

    def render_game_over_screen(self):
        self.game_over_menu = GenericMenu(
            title=f"Game over! {self.game.winner.name} wins!",
            frame_color=(0, 0, 0, 0.5),
            title_pos=(0, 0, 0.55),
        )
        self.game_over_menu.show()

        self.text = {
            "stat_names": OnscreenText(
                text="Points\n",
                style=1,
                fg=(1, 1, 1, 1),
                shadow=(0, 0, 0, 0.5),
                pos=(self.left_most, self.top_most - self.row_spacing),
                scale=self.stat_font_size,
            ),
        }
        for i, player in enumerate(self.game.players):
            self.text[player.name] = OnscreenText(
                text=f"{player.name}\n{player.points}",
                style=1,
                fg=(1, 1, 1, 1),
                shadow=(0, 0, 0, 0.5),
                pos=(self.left_most + self.col_spacing * (i + 1), self.top_most),
                scale=self.stat_font_size,
            )
