from pathlib import Path

from pooltool import System

TEST_DIR = Path(__file__).parent


def prep_shot(path: Path, event_idx: int) -> System:
    shot = System.load(path)
    for ball in shot.balls.values():
        ball.state = ball.history[event_idx]
    shot.reset_history()
    return shot
