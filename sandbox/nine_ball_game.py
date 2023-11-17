from logging import root
from typing import Tuple

import numpy as np
from mcts.mcts import MCTS
from mcts.state import State

import pooltool as pt
from pooltool.game.ruleset.nine_ball import NineBall

GAMETYPE = pt.GameType.NINEBALL


def gen_game() -> Tuple[pt.MultiSystem, pt.System, pt.NineBall]:
    """Create system and games object

    This is called at the start of each game. The created system is placed in a
    multisystem, which will hold all the shots of the game.
    """
    # First create all the objects in the system
    cue = pt.Cue.default()
    table = pt.Table.from_game_type(GAMETYPE)
    balls = pt.get_rack(GAMETYPE, table)

    # Compile the objects into a system
    system = pt.System(
        cue=cue,
        table=table,
        balls=balls,
    )

    # Create a multisystem. Each shot (system) will be stored in this multisystem
    multisystem = pt.MultiSystem()

    # Create a nine ball game
    game = pt.NineBall()

    # Return the multisystem and game
    return multisystem, system, game


def aim(shot: pt.System, game: NineBall) -> Tuple[pt.System, MCTS]:
    """Aim the shot

    This is where an AI could be plugged into
    """
    mcts = MCTS.create(root_state=State(shot, game), breadth=20)

    if game.shot_number == 0:
        shot.aim_at_ball("1")
        shot.strike(V0=8)
        return shot, mcts

    action = mcts.run(600)
    action.apply(shot.cue)
    shot.strike()
    return shot, mcts


games_played = 0
shots, shot, game = gen_game()
gui = pt.ShotViewer()

while True:
    shot, mcts = aim(shot, game)
    shot = pt.simulate(shot, inplace=True)
    game.process_and_advance(shot)
    # gui.show(shot)
    shots.append(shot)
    shot = shot.copy()

    if game.shot_info.game_over or game.shot_number > 30:
        games_played += 1
        print("----")
        print(f"Game {games_played} finished!")
        print(f"\tWinner: {game.shot_info.winner}")
        print(f"\tPoints: {game.shot_info.score}")
        print(f"\tTurns at table: {game.turn_number}")
        print(f"\tShots taken: {game.shot_number}")

        gui.show(shots, "Press [n] and [p] to cycle through shots, [esc] for next game")
        shots, shot, game = gen_game()

    if game.shot_number == 1:
        continue
    ranked = sorted(mcts.root.children, key=lambda child: child.value / child.visits)[
        ::-1
    ]
    for i, child in enumerate(ranked):
        gui.show(
            child.state.system,
            title=f"Option {i}; Rank Value {child.value / child.visits}; Value {child.value}; Visits {child.visits}",
        )
        if i == 5:
            break
