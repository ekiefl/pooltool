from pooltool.evolution.continuize import continuize
from pooltool.evolution.event_based.simulate import simulate
from pooltool.system import System


def test_continuize_inplace():
    # Simulate a system
    system = simulate(System.example())

    # Now continuize it (no inplace)
    continuized_system = continuize(system, inplace=False)

    # Passed system is not continuized
    assert not system.continuized

    # Returned system is
    assert continuized_system.continuized

    # Simulate another system
    system = simulate(System.example())

    # Now continuize it (inplace)
    continuized_system = continuize(system, inplace=True)

    # Passed system is continuized
    assert system.continuized

    # Returned system is continuized
    assert continuized_system.continuized

    # They are the same object
    assert continuized_system is system
