from pooltool.utils.strenum import StrEnum, auto


class BallBallModel(StrEnum):
    """An Enum for different ball-ball collision models

    Attributes:
        FRICTIONLESS_ELASTIC:
            Frictionless, instantaneous, elastic, equal mass collision
            (:class:`FrictionlessElastic`).
    """

    FRICTIONLESS_ELASTIC = auto()
    FRICTIONAL_INELASTIC = auto()
    FRICTIONAL_MATHAVAN = auto()


class BallLCushionModel(StrEnum):
    """An Enum for different ball-linear cushion collision models

    Attributes:
        HAN_2005:
            https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-han-2005
            (:class:`Han2005Linear`).
        UNREALISTIC:
            An unrealistic model in which balls are perfectly reflected. Spin is left
            untouched by the interaction (:class:`UnrealisticLinear`).
    """

    HAN_2005 = auto()
    UNREALISTIC = auto()


class BallCCushionModel(StrEnum):
    """An Enum for different ball-circular cushion collision models

    Attributes:
        HAN_2005:
            https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-han-2005
            (:class:`Han2005Linear`).
        UNREALISTIC:
            An unrealistic model in which balls are perfectly reflected. Spin is left
            untouched by the interaction (:class:`UnrealisticCircular`).
    """

    HAN_2005 = auto()
    UNREALISTIC = auto()


class BallPocketModel(StrEnum):
    """An Enum for different ball-pocket collision models

    Attributes:
        CANONICAL:
            Sets the ball into the bottom of pocket and sets the state to pocketed
            (:class:`CanonicalBallPocket`).
    """

    CANONICAL = auto()


class StickBallModel(StrEnum):
    """An Enum for different stick-ball collision models

    Attributes:
        INSTANTANEOUS_POINT:
            Instantaneous and point-like stick-ball interaction
            (:class:`InstantaneousPoint`).
    """

    INSTANTANEOUS_POINT = auto()


class BallTransitionModel(StrEnum):
    """An Enum for different transition models

    Attributes:
        CANONICAL:
            Sets the ball to appropriate state. Sets any residual quantities to 0 when
            appropriate (:class:`CanonicalTransition`).
    """

    CANONICAL = auto()
