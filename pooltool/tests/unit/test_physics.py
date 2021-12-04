#! /usr/bin/env python
"""Unit testing for physics.py

FIXME My plan for this module is to test each of the functions in physics.py by taking the reference shot
(ref) and parsing its events. For example, resolve_ball_ball_collision could be tested by collecting
every ball-ball collision event in ref, and then creating a new BallBallCollisionEvent with two balls
with states event.ball1_state_start, event.ball2_state_start. Then, by calling event.resolve, I can
ensure event.ball1_state_end, and event.ball2_state.end are produced. The reason this hasn't yet happened
is that I need to create a pickleable representation for the Event object, so that saving/loading/copying
system states preserve event history.
"""

import pooltool.physics as p

from pooltool.tests import trial, ref

def test_resolve_ball_ball_collision(ref):
    pass
