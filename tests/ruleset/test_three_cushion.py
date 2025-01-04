from pathlib import Path

from pooltool.ruleset.three_cushion import is_point
from pooltool.system.datatypes import System

root = Path(__file__).parent

def test_three_cushion():
    shot = System.load(root / "test_shots/01_test_shot_no_point.msgpack")
    assert not is_point(shot)

    shot = System.load(root / "test_shots/01a_test_shot_no_point.msgpack")
    assert not is_point(shot)

    shot = System.load(root / "test_shots/02_test_shot_ispoint.msgpack")
    assert is_point(shot)

    shot = System.load(root / "test_shots/02a_test_shot_ispoint.msgpack")
    assert is_point(shot)

    shot = System.load(root / "test_shots/03_test_shot_ispoint.msgpack")
    assert is_point(shot)

    shot = System.load(root / "test_shots/03a_test_shot_ispoint.msgpack")
    assert is_point(shot)

    shot = System.load(root / "test_shots/04_test_shot_no_point.msgpack")
    assert not is_point(shot)

    shot = System.load(root / "test_shots/04a_test_shot_no_point.msgpack")
    assert not is_point(shot)

    shot = System.load(root / "test_shots/05_test_shot_ispoint.msgpack")
    assert is_point(shot)

    shot = System.load(root / "test_shots/05a_test_shot_ispoint.msgpack")
    assert is_point(shot)