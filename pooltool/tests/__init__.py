#! /usr/bin/env python

import pooltool as pt

from pooltool.error import ConfigError
from pooltool.system import System

from pathlib import Path

import pytest
import numpy as np

data_dir = Path(__file__).parent / 'data'
benchmark_path = data_dir / 'benchmark.pkl'
if not benchmark_path.exists():
    raise ConfigError('benchmark.pkl missing. Run pooltool/tests/get_dataset.py to generate.')

shot_ref = System()
shot_ref.load(benchmark_path)

@pytest.fixture
def ref():
    return shot_ref.copy()

shot_trial = shot_ref.copy()
shot_trial.simulate(continuize=True, dt=0.01)
shot_trial.reset_balls()

@pytest.fixture
def trial():
    return shot_trial
