"""Constants and other

All units are SI unless otherwise stated.
"""

__version__ = "0.1"

from pooltool.ani.animate import Game, ImageSaver, ShotViewer
from pooltool.events import Event, EventType
from pooltool.evolution import simulate
from pooltool.layouts import (
    get_eight_ball_rack,
    get_nine_ball_rack,
    get_three_cushion_rack,
)
from pooltool.objects.ball.datatypes import (
    Ball,
    BallHistory,
    BallOrientation,
    BallParams,
    BallState,
)
from pooltool.objects.cue.datatypes import Cue, CueSpecs
from pooltool.objects.table.components import (
    CircularCushionSegment,
    CushionDirection,
    LinearCushionSegment,
    Pocket,
)
from pooltool.objects.table.datatypes import (
    BilliardTableSpecs,
    PocketTableSpecs,
    Table,
    TableModelDescr,
    TableType,
)
from pooltool.system.datatypes import MultiSystem, System
