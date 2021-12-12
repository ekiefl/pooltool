#! /usr/bin/env python

import pooltool as pt

system = pt.System(path='benchmark_long.pkl')
system.simulate(continuize=True, quiet=True)

interface = pt.ShotViewer()
interface.show(system)

