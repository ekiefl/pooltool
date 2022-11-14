#! /usr/bin/env python

from pooltool.ani.modes.aim import AimMode
from pooltool.ani.modes.ball_in_hand import BallInHandMode
from pooltool.ani.modes.calculate import CalculateMode
from pooltool.ani.modes.call_shot import CallShotMode
from pooltool.ani.modes.cam_load import CamLoadMode
from pooltool.ani.modes.cam_save import CamSaveMode
from pooltool.ani.modes.datatypes import BaseMode, Mode, ModeManager
from pooltool.ani.modes.game_over import GameOverMode
from pooltool.ani.modes.menu import MenuMode
from pooltool.ani.modes.pick_ball import PickBallMode
from pooltool.ani.modes.purgatory import PurgatoryMode
from pooltool.ani.modes.shot import ShotMode
from pooltool.ani.modes.stroke import StrokeMode
from pooltool.ani.modes.view import ViewMode

all_modes = {cls.name: cls for cls in BaseMode.__subclasses__()}


__all__ = [
    "Mode",
    "ModeManager",
    "AimMode",
    "BallInHandMode",
    "CalculateMode",
    "CallShotMode",
    "CamLoadMode",
    "CamSaveMode",
    "GameOverMode",
    "MenuMode",
    "PickBallMode",
    "PurgatoryMode",
    "ShotMode",
    "StrokeMode",
    "ViewMode",
]
