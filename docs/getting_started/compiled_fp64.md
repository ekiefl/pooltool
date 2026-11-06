# Compiled FP64 simulation

Pooltool's experimental CPU backend runs the stock planar event loop on
FP64 arrays using Numba. Select it explicitly with
`simulate(..., backend="compiled_fp64")`. Ordinary calls still use the
reference simulator.

```python
import numpy as np
import pooltool as pt
from pooltool.evolution.engine import SimulationEngine
from pooltool.physics.resolve.resolver import default_resolver

engine = SimulationEngine(resolver=default_resolver())
shot = pt.System.example()
reference = pt.simulate(shot, engine=engine, continuous=True, dt=0.01)
compiled = pt.simulate(
    shot, engine=engine, backend="compiled_fp64", continuous=True, dt=0.01
)

assert [(e.event_type, e.ids) for e in compiled.events] == [
    (e.event_type, e.ids) for e in reference.events
]
np.testing.assert_allclose(
    [e.time for e in compiled.events], [e.time for e in reference.events],
    atol=50e-9, rtol=0,
)
compiled.save("compiled-shot.msgpack")
reopened = pt.System.load("compiled-shot.msgpack")
assert reopened == compiled
```

The explicit engine in the example selects stock models even if a user
has configured another default resolver.

## Supported configurations

| Boundary | Compiled support |
| --- | --- |
| Detector | Canonical planar `EventDetector`. |
| Resolver | Frictional-inelastic 2D with Alciatore friction, Stronge-compliant 2D linear and circular cushions, instantaneous-point 2D cue impact, canonical pocket and motion transitions. |
| Table | Native planar geometry with standard linear cushions, circular jaws and pockets. Geometry and supported model parameters are read from the objects. |
| Ball state | Finite native FP64 states with equal radii and masses. On-table stationary, spinning, sliding and rolling states, and pocketed balls. Cloth and restitution parameters may vary by ball within the validated parameter bounds. |
| Results | Native events, event snapshots, ball and pocket states, sparse history, optional continuous history, and standard serialization. |
| Options | Copy or in-place simulation, `continuous`, positive finite `dt` when interpolating, `t_final`, and `max_events` with reference stopping behavior. |

Custom detectors, custom event inclusion, other collision strategies,
airborne or off-table states, and unequal masses or radii are outside the
supported scope. Unsupported inputs raise `ValueError` before mutation.
Numerical failures and the 4,096-event internal history limit raise
`SimulateError`. A failed in-place call leaves the input intact. The backend
does not fall back to the reference simulator.

## Warm-up and testing

Run a representative compiled shot once before timing a batch. The first
compiled call incurs compilation or disk-cache loading. The ordinary
import and reference calls do not initialize the compiled event loop.
Set Numba's `NUMBA_CACHE_DIR` to a writable absolute directory before
importing Pooltool to make the cache location explicit. Use a fresh
directory after switching code revisions or dependency versions.

Run the routine checks with
`uv run pytest tests/evolution/event_based/test_compiled_fp64.py`.
Set `POOLTOOL_EXTENDED_FP64=1` to add the seeded differential sweep.
These compare against the reference simulator using absolute bounds of
50 ns in time, 0.5 µm in position, 0.5 µm/s in velocity and 0.0001 rad/s in
spin, with exact event categories, participants and order. These bounds
describe software comparisons.
