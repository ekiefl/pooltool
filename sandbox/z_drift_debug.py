from pooltool import MultiSystem, ShotViewer, System
from pooltool.constants import pocketed

BROKEN_MULTISYSTEM = "debug.msgpack"

multisystem = MultiSystem.load(BROKEN_MULTISYSTEM)

idx = 0
for system in multisystem:
    for ball in system.balls.values():
        for state in ball.history:
            # We don't care about pocketed states
            if state.s == pocketed:
                continue

            # Does the ball's z position equal it's radius?
            if state.rvw[0, 2] != ball.params.R:
                print(idx, ball.id)
                break

    idx += 1

interface = ShotViewer()
interface.show(multisystem[4])
