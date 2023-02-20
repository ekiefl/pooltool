from dataclasses import FrozenInstanceError

import pytest

from pooltool.objects.cue.datatypes import Cue


def test_cue_copy():
    cue = Cue()
    copy = cue.copy()

    # `specs` is frozen
    with pytest.raises(FrozenInstanceError):
        cue.specs.brand = "brunswick"

    # cue and copy equate
    assert cue == copy

    # modifying cue doesn't affect copy
    cue.phi += 1
    assert cue != copy
    assert cue.phi != copy.phi
