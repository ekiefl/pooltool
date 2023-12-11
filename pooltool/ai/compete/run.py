from pathlib import Path
from typing import Protocol, Tuple

from pooltool.ai.bot import AimNaiveAI, AimPocketAI, WorstAI
from pooltool.ai.bot.sumtothree_rl.core import ActionInference, SumToThreeAI
from pooltool.ai.compete.result import ResultAccumulator, ShotResult
from pooltool.evolution.event_based.simulate import simulate
from pooltool.game.datatypes import GameType
from pooltool.game.layouts import get_rack
from pooltool.game.ruleset import get_ruleset
from pooltool.game.ruleset.datatypes import Player, Ruleset
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.system.datatypes import MultiSystem, System


class GetAI(Protocol):
    def __call__(self, game: Ruleset) -> Player:
        ...


def gen_game(
    game_type: GameType, gen_ai_1: GetAI, gen_ai_2: GetAI
) -> Tuple[MultiSystem, System, Ruleset]:
    system = System(
        cue=Cue.default(),
        table=(table := Table.from_game_type(game_type)),
        balls=get_rack(game_type, table),
    )

    game = get_ruleset(game_type)()
    game.players = [
        gen_ai_1(game),
        gen_ai_2(game),
    ]

    return MultiSystem(), system, game


def compete(
    game_type: GameType,
    games: int,
    gen_ai_1: GetAI,
    gen_ai_2: GetAI,
    quiet: bool = True,
) -> ResultAccumulator:
    games_played = 0
    shots, shot, game = gen_game(game_type, gen_ai_1, gen_ai_2)
    results = ResultAccumulator()

    while True:
        player = game.active_player
        assert player.ai is not None
        action = player.ai.decide(shot, game)
        player.ai.apply(shot, action)

        simulate(shot, inplace=True, max_events=500)
        if shot.get_system_energy() > 0:
            # For whatever reason, the shot evolver get stuck
            shots, shot, game = gen_game(game_type, gen_ai_1, gen_ai_2)
            continue

        game.process_and_advance(shot)

        shots.append(shot)

        shot = shot.copy()
        shot.reset_history()

        results.add(ShotResult.from_shot_info(game.shot_info))

        if game.shot_info.game_over or game.shot_number > 100:
            games_played += 1

            if not quiet:
                print(f"Game {games_played} finished!")
                print(f"\tWinner: {game.shot_info.winner}")

            if games_played == games:
                break

            shots, shot, game = gen_game(game_type, gen_ai_1, gen_ai_2)

    return results


if __name__ == "__main__":
    model_path = Path("/Users/evan/Software/pooltool_ml/LightZero/data_pooltool_ctree/trial0/ckpt/ckpt_best.pth.tar")
    model = ActionInference.from_model_path(model_path)

    results = compete(
        game_type=GameType.SUMTOTHREE,
        games=50,
        gen_ai_1=lambda game: Player(
            "Bot 1", ai=SumToThreeAI.load(model_path)
        ),
        gen_ai_2=lambda game: Player(
            "Bot 2", ai=SumToThreeAI.load(model_path)
        ),
        quiet=False,
    )
    results.plot_summary()
