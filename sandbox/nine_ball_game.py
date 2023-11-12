from typing import Tuple

import numpy as np

import pooltool as pt
from pooltool.game.ruleset.utils import get_lowest_ball

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


def aim(shot: pt.System) -> pt.System:
    """Aim the shot

    This is where an AI could be plugged into
    """
    if GAMETYPE != pt.GameType.NINEBALL:
        raise NotImplementedError("This aim() method doesn't work for other games")

    cue = shot.cue
    shot.aim_for_best_pocket(get_lowest_ball(shot, at_start=False).id)
    shot.strike(
        V0=4.5 * np.random.rand() + 0.5,
        phi=pt.math.wiggle(cue.phi, 0.5),
        a=np.random.rand() - 0.5,
        b=np.random.rand() - 0.5,
        theta=3,
    )

    return shot


games_played = 0
shots, shot, game = gen_game()
gui = pt.ShotViewer()

while True:
    shot = pt.simulate(aim(shot), inplace=True)
    game.process_and_advance(shot)
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
