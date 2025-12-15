from pooltool.utils.strenum import StrEnum, auto


class BallBallModel(StrEnum):
    """An Enum for different ball-ball collision models

    Attributes:
        FRICTIONLESS_ELASTIC:
            A frictionless, instantaneous, elastic, equal mass collision resolver.

            This is as simple as it gets.

            See Also:
                - This physics of this model is blogged about at
                  https://ekiefl.github.io/2020/04/24/pooltool-theory/#1-elastic-instantaneous-frictionless

        FRICTIONAL_INELASTIC:
            A simple ball-ball collision model including ball-ball friction, and
            coefficient of restitution for equal-mass balls.

            Largely inspired by Dr. David Alciatore's technical proofs
            (https://billiards.colostate.edu/technical_proofs), in particular, TP_A-5, TP_A-6,
            and TP_A-14. These ideas have been extended to include motion of both balls, and a
            more complete analysis of velocity and angular velocity in their vector forms.

        FRICTIONAL_MATHAVAN:
            Ball-ball collision resolver for the Mathavan et al. (2014) collision model.

            The model "uses general theories of dynamics of spheres rolling on a flat surface and
            general frictional impact dynamics under the assumption of point contacts between the
            balls under collision and that of the table."

            The authors compare the model predictions to experimental exit velocities and angles
            measured with a high speed camera system and illustrate marked improvement over previous
            theories, which unlike this model, fail to account for spin.

            References:
                Mathavan, S., Jackson, M.R. & Parkin, R.M. Numerical simulations of the frictional
                collisions of solid balls on a rough surface. Sports Eng 17, 227–237 (2014).
                https://doi.org/10.1007/s12283-014-0158-y

                Available at
                https://billiards.colostate.edu/physics_articles/Mathavan_Sports_2014.pdf
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

        IMPULSE_FRICTIONAL_INELASTIC:
            An instantaneous/non-smooth, impulse-based collision model.  This model includes effects of
            tangential friction and normal coefficient of restitution.

        MATHAVAN_2010:
            Ball-cushion collision resolver for the Mathavan et al. (2010) collision model.

            This work predicts ball bounce angles and bounce speeds for the ball’s collisions
            with a cushion, under the assumption of insignificant cushion deformation.
            Differential equations are derived for the ball dynamics during the impact and these
            these equations are solved numerically.

            References:
                Mathavan S, Jackson MR, Parkin RM. A theoretical analysis of billiard
                ball-cushion dynamics under cushion impacts. Proceedings of the Institution of
                Mechanical Engineers, Part C. 2010;224(9):1863-1873.
                doi:10.1243/09544062JMES1964

                Available at
                https://drdavepoolinfo.com//physics_articles/Mathavan_IMechE_2010.pdf

        STRONGE_COMPLIANT:
            An instantaneous/non-smooth, collision model that accounts for tangential compliance.
            This model includes effects of tangential friction, tangential compliance, and normal
            coefficient of restitution. Accounting for tangential compliance allows for reversal
            of the slip direction at the contact point.

            This model assumes the colliding bodies (ball and rail) are rigid bodies, one of which
            is connected at the contact point to a massless particle via two independent springs.
            One of the springs is oriented in the normal direction, the other in the tangent
            direction. During restitution, the stiffness of the normal spring increases depending
            on the coefficient of restitution. The tangential spring has a constant stiffness. This
            results in simple harmonic motion in both the normal and tangent directions. These
            equations can be solved for the final velocities after some root finding to determine
            transitions between sticking and slipping at the contact point. There is no numerical
            integration to solve for the final result.

            References:
                W. J. Stronge, “Tangential Compliance in Planar Impact of Rough Bodies,” in Impact Mechanics,
                Cambridge: Cambridge University Press, 2018, pp. 89–115
                doi:10.1017/9781139050227
    """

    MATHAVAN_2010 = auto()
    HAN_2005 = auto()
    IMPULSE_FRICTIONAL_INELASTIC = auto()
    STRONGE_COMPLIANT = auto()
    UNREALISTIC = auto()


class BallCCushionModel(StrEnum):
    """An Enum for different ball-circular cushion collision models

    Attributes:
        HAN_2005: See :class:`BallLCushionModel`.
        UNREALISTIC: See :class:`BallLCushionModel`.
        IMPULSE_FRICTIONAL_INELASTIC: See :class:`BallLCushionModel`.
        MATHAVAN_2010: See :class:`BallLCushionModel`.
        STRONGE_COMPLIANT: See :class:`BallLCushionModel`.
    """

    MATHAVAN_2010 = auto()
    HAN_2005 = auto()
    IMPULSE_FRICTIONAL_INELASTIC = auto()
    STRONGE_COMPLIANT = auto()
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

            This collision assumes the stick-ball interaction is instantaneous and point-like.

            Note:
                - A derivation of this model can be found in Dr. Dave Billiard's technical proof
                  A-30 (https://billiards.colostate.edu/technical_proofs/new/TP_A-30.pdf)

            Additionally, a deflection (squirt) angle is calculated via
            :mod:`pooltool.physics.resolve.stick_ball.squirt`).
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
