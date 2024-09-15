# Hello World

[The Interface](interface) can be accessed not just from the command line, but also programmatically. In this section, you'll create a script that creates a billiards system, simulates it, and then visualizes it with the interface.

Consider this *hello world* for pooltool.

## Script

For those that want to jump straight in, here is the script:

```python
#! /usr/bin/env python

import pooltool as pt

# We need a table, some balls, and a cue stick
table = pt.Table.default()
balls = pt.get_rack(pt.GameType.NINEBALL, table)
cue = pt.Cue(cue_ball_id="cue")

# Wrap it up as a System
shot = pt.System(table=table, balls=balls, cue=cue)

# Aim at the head ball with a strong impact
shot.cue.set_state(V0=8, phi=pt.aim.at_ball(shot, "1"))

# Evolve the shot.
pt.simulate(shot, inplace=True)

# Open up the shot in the GUI
pt.show(shot)
```

For those interested in some exposition, below is a line-by-line explanation.

## Explanation

First thing first, the pootool package is imported which gives you access to the {py:mod}`top-level API <pooltool>`:

```python
import pooltool as pt
```

Then a table, a cue stick, and a collection of balls are created and wrapped up into a {py:class}`System <pooltool.System>`:

```python
# We need a table, some balls, and a cue stick
table = pt.Table.default()
balls = pt.get_rack(pt.GameType.NINEBALL, table)
cue = pt.Cue(cue_ball_id="cue")

# Wrap it up as a System
shot = pt.System(table=table, balls=balls, cue=cue)
```

The cue stick parameters are then set with {py:meth}`pooltool.Cue.set_state`. A large impact speed of `V0=8` (m/s) is chosen, and an aiming utility function is used to aim the cue ball directly at the one-ball.

```python
# Aim at the head ball with a strong impact
shot.cue.set_state(V0=8, phi=pt.aim.at_ball(shot, "1"))
```

:::{admonition} Cue Signature

A description of the cue's parameters can be found in the API docs:

```{eval-rst}
.. autoclass:: pooltool.Cue
    :noindex:
```
:::

The cue parameters have been set, but the system still hasn't been simulated. This is done with a call to {py:func}`pooltool.simulate`.

```python
# Evolve the shot.
pt.simulate(shot, inplace=True)
```

The system has now been evolved from its initial to its final state.

To visualize the shot, open the GUI with {py:func}`pooltool.show`:

```python
# Open up the shot in the GUI
pt.show(shot)
```

## Next

Obviously this script is just the beginning. Pooltool offers much more than this, which means you have much more to learn. From here, I suggest you check out the [Examples](../examples/index.md) page and dive into whatever topic interests you.
