#! /usr/bin/env python

import pooltool.ani.utils as autils
from pooltool.ani.action import Action
from pooltool.ani.globals import Global
from pooltool.ani.menu import GenericMenu
from pooltool.ani.modes.datatypes import BaseMode, Mode
from pooltool.ani.mouse import MouseMode, mouse


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
        mouse.mode(MouseMode.ABSOLUTE)

        self.register_keymap_event("escape", Action.quit, True)
        self.render_game_over_screen()

    def exit(self):
        self.game_over_menu.hide()
        for text in self.text.values():
            text.hide()

        del self.game_over_menu
        del self.text

    def render_game_over_screen(self):
        if (winner := Global.game.shot_info.winner) is not None:
            title = f"Game over! {winner.name} wins!"
        else:
            title = "Game over! Tie game!"

        self.game_over_menu = GenericMenu(
            title=title,
            frame_color=(0, 0, 0, 0.5),
            title_pos=(0, 0, 0.55),
        )
        self.game_over_menu.show()

        self.text = {
            "stat_names": autils.CustomOnscreenText(
                text="Points\n",
                style=1,
                fg=(1, 1, 1, 1),
                shadow=(0, 0, 0, 0.5),
                pos=(self.left_most, self.top_most - self.row_spacing),
                scale=self.stat_font_size,
            ),
        }
        for i, player in enumerate(Global.game.players):
            points = Global.game.score[player.name]
            self.text[player.name] = autils.CustomOnscreenText(
                text=f"{player.name}\n{points}",
                style=1,
                fg=(1, 1, 1, 1),
                shadow=(0, 0, 0, 0.5),
                pos=(self.left_most + self.col_spacing * (i + 1), self.top_most),
                scale=self.stat_font_size,
            )
