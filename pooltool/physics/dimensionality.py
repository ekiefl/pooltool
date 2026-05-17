from pooltool.utils.strenum import StrEnum, auto


class Dim(StrEnum):
    """Dimensionality capability declaration for physics strategies.

    Each Resolver and EventDetector strategy declares one of these as a class-level
    attribute. :class:`pooltool.evolution.engine.SimulationEngine` reads these once at
    construction to validate that the bundled strategies are compatible with its
    ``is_3d`` setting.

    A strategy's ``dim`` is a promise about its behavior, *not* a mode switch.
    ``BOTH`` means the strategy behaves identically in either mode; it does not mean
    the strategy branches internally based on mode. If a strategy would behave
    differently in 2D vs 3D, it should be split into separate ``TWO`` and ``THREE``
    classes.

    Members:
        TWO: Safe only when ``SimulationEngine.is_3d`` is ``False``.
        THREE: Safe only when ``SimulationEngine.is_3d`` is ``True``.
        BOTH: Behavior identical in either mode; safe always.
    """

    TWO = auto()
    THREE = auto()
    BOTH = auto()
