#! /usr/bin/env python

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

import psim.utils as utils
import psim.engine as engine

engine.include = {
    'motion': True,
    'ball_ball': True,
    'ball_cushion': True,
}

def setup():
    """Return a shot object that is ready for simulation"""
    shot = engine.ShotSimulation()
    shot.setup_test('straight_shot')
    shot.cue.strike(
        ball = shot.balls['cue'],
        V0 = 1.35,
        phi = 97,
        a = 0.3,
        b = -0.3,
        theta = 10,
    )
    return shot

def is_accurate(shot, true_shot):
    """Tests if series of events matches event-based event history"""
    true_history = [(event.event_type, event.agents)
                    for event in true_shot.history['event']
                    if event is not None
                    and event.event_type in ('ball-ball', 'ball-rail')]
    history = [(event.event_type, event.agents)
               for event in shot.history['event']
               if event is not None]

    return True if history == true_history else False

# Simulate using event-based algorithm and store time taken
cts_shot = setup()
with utils.TimeCode() as t:
    cts_shot.simulate_event_based()
cts_time = t.time.total_seconds()

# Init a dict that stores discrete time simulation stats
results = {
    'dt': [],
    'time': [],
    'accurate': [],
}

# Run many discrete time simulation with decreasing timestep
for dt in np.logspace(0, -4.5, 30):
    shot = setup()
    with utils.TimeCode() as t:
        shot.simulate_discrete_time(dt)

    results['dt'].append(dt)
    results['time'].append(t.time.total_seconds())
    results['accurate'].append('accurate' if is_accurate(shot, cts_shot) else 'inaccurate')

results = pd.DataFrame(results)

sns.scatterplot(data=results, x='dt', y='time', hue='accurate')
plt.plot([results['dt'].min(), results['dt'].max()], [cts_time, cts_time], label='event-based', c='green')
plt.xscale('log')
plt.yscale('log')
plt.xlabel('Timestep [s]')
plt.ylabel('Calculation time [s]')
plt.legend(loc='best')
plt.tight_layout()
plt.show()
