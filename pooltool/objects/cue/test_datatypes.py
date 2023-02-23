from dataclasses import FrozenInstanceError

import pytest

from pooltool.objects.cue.datatypes import Cue


def test_cue_copy():
    cue = Cue()
    copy = cue.copy()

    # cue and copy equate
    assert cue == copy

    # The specs are the same object but thats ok because `specs` is frozen
    assert cue.specs is copy.specs
    with pytest.raises(FrozenInstanceError):
        cue.specs.brand = "brunswick"

    # modifying cue doesn't affect copy
    cue.phi += 1
    assert cue != copy
    assert cue.phi != copy.phi
