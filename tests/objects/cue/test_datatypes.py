import pytest
from attrs.exceptions import FrozenInstanceError

from pooltool.game.datatypes import GameType
from pooltool.objects.cue.datatypes import Cue, CueSpecs, PrebuiltCueSpecs


def test_cue_copy():
    cue = Cue()
    copy = cue.copy()

    # cue and copy equate
    assert cue == copy

    # The specs are the same object but thats ok because `specs` is frozen
    assert cue.specs is copy.specs
    with pytest.raises(FrozenInstanceError):
        cue.specs.brand = "brunswick"  # type: ignore

    # modifying cue doesn't affect copy
    cue.phi += 1
    assert cue != copy
    assert cue.phi != copy.phi


def test_cue_specs_construction():
    # Can't instantiate without setting parameters
    with pytest.raises(TypeError):
        CueSpecs()  # type: ignore

    # All prebuilt/default methods construct properly
    CueSpecs.default()
    CueSpecs.default(GameType.SNOOKER)
    CueSpecs.prebuilt(PrebuiltCueSpecs.POOL_GENERIC)


def test_cue_from_game_type():
    assert Cue.from_game_type(GameType.EIGHTBALL).specs == CueSpecs.default()
    assert Cue.from_game_type(GameType.SNOOKER).specs == CueSpecs.default(
        GameType.SNOOKER
    )

    # ID is passed through
    assert Cue.from_game_type(GameType.SNOOKER).id == "cue_stick"
    assert Cue.from_game_type(GameType.SNOOKER, id="other").id == "other"


def test_cue_from_game_type_unknown():
    with pytest.raises(NotImplementedError):
        Cue.from_game_type("unknown_game")  # type: ignore
