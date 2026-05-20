from pooltool.utils.strenum import StrEnum, auto


class Dim(StrEnum):
    """Dimensionality capability declaration for physics strategies.

    Each Resolver and EventDetector strategy declares one of these as a class-level
    attribute. :class:`pooltool.evolution.SimulationEngine` reads these once at
    construction to validate that the bundled strategies are compatible with its
    ``is_3d`` setting.

    A strategy's ``dim`` is a promise about *safety*, not behavior. Strategies
    don't see ``SimulationEngine.is_3d`` - they see only the inputs handed to
    them and must remain correct under the states their mode can produce.
    ``BOTH`` is appropriate when the strategy is safe in either mode. It may
    still take different code paths depending on the input (e.g. a branch on
    ``state == const.airborne`` is dead in 2D and live in 3D), as long as
    neither path is incorrect for the mode it runs under.

    Members:
        TWO: Safe only when ``SimulationEngine.is_3d`` is ``False``.
        THREE: Safe only when ``SimulationEngine.is_3d`` is ``True``.
        BOTH: Safe in either mode.
    """

    TWO = auto()
    THREE = auto()
    BOTH = auto()


SKIP_DIMENSION: frozenset[str] = frozenset({"ball_table"})
"""Resolver/EventDetector field names whose strategies don't carry a ``dim``
attribute. ``SimulationEngine._validate_dimensionality`` skips these fields
entirely (in either mode). Used for slots whose events have no meaning in 2D
(currently just ``ball_table``: airborne balls only exist in 3D)."""
