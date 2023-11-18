from typing import Tuple

import pooltool as pt
from pooltool.evolution.event_based.simulate import simulate

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


games_played = 0
shots, shot, game = gen_game()
ai = pt.ai.UnintelligentAI(game)
gui = pt.ShotViewer()

while True:
    # Take a shot
    action = ai.decide(shot)
    ai.apply(shot, action)
    simulate(shot, inplace=True)
    game.process_and_advance(shot)

    # Add shot to multisystem
    shots.append(shot)

    # Create a shot for next iteration
    shot = shot.copy()
    shot.reset_history()

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
