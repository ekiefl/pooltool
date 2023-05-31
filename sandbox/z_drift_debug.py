from pooltool import MultiSystem, ShotViewer, System
from pooltool.constants import pocketed

BROKEN_MULTISYSTEM = "debug.msgpack"

multisystem = MultiSystem.load(BROKEN_MULTISYSTEM)

for system in multisystem:
    for state in system.balls["cue"].history:
        if state.s == pocketed:
            print("pocketed")
            continue
        print(state.rvw[0, 2])

interface = ShotViewer()
interface.show(multisystem[4])
