"""Simulation object classes

The three main simulation objects are :class:`pooltool.objects.ball.datatypes.Ball`,
:class:`pooltool.objects.cue.datatypes.Cue`, and
:class:`pooltool.objects.table.datatypes.Table`, however there are many more objects
that either help create the primary objects or comprise the primary objects. Those are
all kept in this module.
"""

from pooltool.objects.ball.datatypes import (
    Ball,
    BallHistory,
    BallOrientation,
    BallParams,
    BallState,
)
from pooltool.objects.ball.sets import BallSet, get_ballset
from pooltool.objects.cue.datatypes import Cue, CueSpecs
from pooltool.objects.table.components import (
    CircularCushionSegment,
    CushionDirection,
    CushionSegments,
    LinearCushionSegment,
    Pocket,
)
from pooltool.objects.table.datatypes import Table
from pooltool.objects.table.specs import (
    BilliardTableSpecs,
    PocketTableSpecs,
    SnookerTableSpecs,
    TableModelDescr,
    TableType,
)

__all__ = [
    "BallSet",
    "Ball",
    "BallState",
    "BallParams",
    "BallHistory",
    "BallOrientation",
    "CueSpecs",
    "Cue",
    "Pocket",
    "LinearCushionSegment",
    "CircularCushionSegment",
    "CushionSegments",
    "CushionDirection",
    "Table",
    "TableModelDescr",
    "TableType",
    "PocketTableSpecs",
    "BilliardTableSpecs",
    "SnookerTableSpecs",
    "get_ballset",
]
