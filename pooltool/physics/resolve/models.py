from pooltool.utils.strenum import StrEnum, auto


class BallBallModel(StrEnum):
    """An Enum for different ball-ball collision models

    Attributes:
        FRICTIONLESS_ELASTIC:
            Frictionless, instantaneous, elastic, equal mass collision.
        FRICTIONAL_INELASTIC:
            Frictional, inelastic, equal mass collision.
            (https://billiards.colostate.edu/technical_proofs/new/TP_A-14.pdf).
        FRICTIONAL_MATHAVAN:
            Mathavan, S., Jackson, M.R. & Parkin, R.M. Numerical simulations of the
            frictional collisions of solid balls on a rough surface. Sports Eng 17,
            227–237 (2014). https://doi.org/10.1007/s12283-014-0158-y
    """

    FRICTIONLESS_ELASTIC = auto()
    FRICTIONAL_INELASTIC = auto()
    FRICTIONAL_MATHAVAN = auto()


class BallLCushionModel(StrEnum):
    """An Enum for different ball-linear cushion collision models

    Attributes:
        HAN_2005:
            https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-han-2005.
        UNREALISTIC:
            An unrealistic model in which balls are perfectly reflected. Spin is left
            untouched by the interaction.
    """

    MATHAVAN_2010 = auto()
    HAN_2005 = auto()
    UNREALISTIC = auto()


class BallCCushionModel(StrEnum):
    """An Enum for different ball-circular cushion collision models

    Attributes:
        HAN_2005:
            https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-han-2005
        UNREALISTIC:
            An unrealistic model in which balls are perfectly reflected. Spin is left
            untouched by the interaction.
    """

    MATHAVAN_2010 = auto()
    HAN_2005 = auto()
    UNREALISTIC = auto()


class BallPocketModel(StrEnum):
    """An Enum for different ball-pocket collision models

    Attributes:
        CANONICAL:
            Sets the ball into the bottom of pocket and sets the state to pocketed.
    """

    CANONICAL = auto()


class StickBallModel(StrEnum):
    """An Enum for different stick-ball collision models

    Attributes:
        INSTANTANEOUS_POINT:
            Instantaneous and point-like stick-ball interaction.
    """

    INSTANTANEOUS_POINT = auto()


class BallTransitionModel(StrEnum):
    """An Enum for different transition models

    Attributes:
        CANONICAL:
            Sets the ball to appropriate state. Sets any residual quantities to 0 when
            appropriate.
    """

    CANONICAL = auto()
