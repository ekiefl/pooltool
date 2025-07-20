import numpy as np

import pooltool as pt

template = pt.System.example()
template.balls["cue"].state.rvw[0, 0] = 0.3
template.cue.set_state(a=0, b=0.4, phi=pt.aim.at_ball(template, "1") + 2.5)

systems = []
for V0 in np.linspace(1, 3, 20):
    system = template.copy()
    system.cue.set_state(V0=V0)
    pt.simulate(system, inplace=True)
    systems.append(system)

pt.show(pt.MultiSystem(systems))
