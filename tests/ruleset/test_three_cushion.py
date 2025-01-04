# from pooltool.ruleset.three_cushion import is_point
# from pooltool.system.datatypes import load

def test_three_cushion():
    # testing function ispoint() with predefined shots
    shot = load("01_test_shot_no_point.msgpack")
    assert is_point(shot) == False

    shot = load("01a_test_shot_no_point.msgpack")
    assert is_point(shot) == False

    shot = load("02_test_shot_ispoint.msgpack")
    assert is_point(shot) == False

    shot = load("02a_test_shot_ispoint.msgpack")
    assert is_point(shot) == False

    shot = load("03_test_shot_ispoint.msgpack")
    assert is_point(shot) == False

    shot = load("03a_test_shot_ispoint.msgpack")
    assert is_point(shot) == False

    shot = load("04_test_shot_no_point.msgpack")
    assert is_point(shot) == False

    shot = load("04a_test_shot_no_point.msgpack")
    assert is_point(shot) == False

    shot = load("05_test_shot_ispoint.msgpack")
    assert is_point(shot) == False

    shot = load("05a_test_shot_ispoint.msgpack")
    assert is_point(shot) == False


