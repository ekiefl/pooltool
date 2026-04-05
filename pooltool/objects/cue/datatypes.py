#! /usr/bin/env python

from __future__ import annotations

from attrs import define, evolve, field, fields_dict

from pooltool.game.datatypes import GameType
from pooltool.utils.strenum import StrEnum, auto


@define(frozen=True)
class CueSpecs:
    """Cue stick specifications.

    All units are SI.

    Attributes:
        brand:
            The brand.
        M:
            The mass.
        length:
            The cue length.
        tip_radius:
            The cue tip radius.
        shaft_radius_at_tip:
            The cue shaft radius near the tip of the cue.
        shaft_radius_at_butt:
            The cue shaft radius near the butt of the cue.
        end_mass:
            The mass of the of the cue's end. This controls the amount of deflection
            (squirt) that occurs when using sidespin. Lower means less deflection. It is
            defined here: https://drdavepoolinfo.com/technical_proofs/new/TP_A-31.pdf.
    """

    brand: str = field()
    M: float = field()
    length: float = field()
    tip_radius: float = field()
    shaft_radius_at_tip: float = field()
    shaft_radius_at_butt: float = field()
    end_mass: float = field()

    @classmethod
    def default(cls, game_type: GameType = GameType.EIGHTBALL) -> CueSpecs:
        """Return prebuilt cue specs based on game type.

        Args:
            game_type:
                What type of game is being played?

        Returns:
            The prebuilt cue specs associated with the passed game type.
        """
        return _get_default_cue_specs(game_type)

    @classmethod
    def prebuilt(cls, name: PrebuiltCueSpecs) -> CueSpecs:
        """Return prebuilt cue specs based on name.

        Args:
            name:
                A :class:`PrebuiltCueSpecs` member.
        """
        return _prebuilt_cue_specs(name)


class PrebuiltCueSpecs(StrEnum):
    """An Enum specifying prebuilt cue specs.

    Attributes:
        POOL_GENERIC:
        SNOOKER_GENERIC:
        BILLIARD_GENERIC:
    """

    POOL_GENERIC = auto()
    SNOOKER_GENERIC = auto()
    BILLIARD_GENERIC = auto()


CUE_MODELS: dict[PrebuiltCueSpecs, str] = {
    PrebuiltCueSpecs.POOL_GENERIC: "cue",
    PrebuiltCueSpecs.SNOOKER_GENERIC: "cue_snooker",
    PrebuiltCueSpecs.BILLIARD_GENERIC: "cue",
}

CUE_SPECS: dict[PrebuiltCueSpecs, CueSpecs] = {
    PrebuiltCueSpecs.POOL_GENERIC: CueSpecs(
        brand="Pooltool",
        M=0.567,
        length=1.4732,
        tip_radius=0.0106045,
        shaft_radius_at_tip=0.0065,
        shaft_radius_at_butt=0.02,
        end_mass=0.170097 / 30,
    ),
    PrebuiltCueSpecs.SNOOKER_GENERIC: CueSpecs(
        brand="Pooltool",
        M=0.478,
        length=1.475,
        tip_radius=0.0106045,
        shaft_radius_at_tip=0.0049,
        shaft_radius_at_butt=0.0124,
        end_mass=0.140 / 30,
    ),
    # TODO: These are just copied from the pool cue specs
    PrebuiltCueSpecs.BILLIARD_GENERIC: CueSpecs(
        brand="Pooltool",
        M=0.567,
        length=1.4732,
        tip_radius=0.0106045,
        shaft_radius_at_tip=0.0065,
        shaft_radius_at_butt=0.02,
        end_mass=0.210 / 30,
    ),
}

_default_map: dict[GameType, PrebuiltCueSpecs] = {
    GameType.EIGHTBALL: PrebuiltCueSpecs.POOL_GENERIC,
    GameType.NINEBALL: PrebuiltCueSpecs.POOL_GENERIC,
    GameType.THREECUSHION: PrebuiltCueSpecs.BILLIARD_GENERIC,
    GameType.SNOOKER: PrebuiltCueSpecs.SNOOKER_GENERIC,
    GameType.SUMTOTHREE: PrebuiltCueSpecs.BILLIARD_GENERIC,
}


def _get_default_cue_specs(game_type: GameType) -> CueSpecs:
    return _prebuilt_cue_specs(_default_map[game_type])


def _prebuilt_cue_specs(name: PrebuiltCueSpecs) -> CueSpecs:
    return CUE_SPECS[name]


@define
class Cue:
    """A cue stick.

    Attributes:
        id:
            An ID for the cue.
        V0:
            The impact speed.

            Units are *m/s*.

            Note:
                This is the speed of the cue stick upon impact, not the speed of the
                ball upon impact.
        phi:
            The directional strike angle.

            The horizontal direction of the cue's orientation relative to the table layout.
            **Specified in degrees**.

            If you imagine facing from the head rail (where the cue is positioned for a
            break shot) towards the foot rail (where the balls are racked),

            - :math:`\\phi = 0` corresponds to striking the cue ball to the right
            - :math:`\\phi = 90` corresponds to striking the cue ball towards the foot rail
            - :math:`\\phi = 180` corresponds to striking the cue ball to the left
            - :math:`\\phi = 270` corresponds to striking the cue ball towards the head rail
            - :math:`\\phi = 360` corresponds to striking the cue ball to the right
        theta:
            The cue inclination angle.

            The vertical angle of the cue stick relative to the table surface. **Specified
            in degrees**.

            - :math:`\\theta = 0` corresponds to striking the cue ball parallel with the
              table (no massé)
            - :math:`\\theta = 90` corresponds to striking the cue ball downwards into the
              table (max massé)
        a:
            The amount and direction of side spin.

            - :math:`a = -1` is the rightmost side of ball
            - :math:`a = +1` is the leftmost side of the ball
        b:
            The amount of top/bottom spin.

            - :math:`b = -1` is the bottom-most side of the ball
            - :math:`b = +1` is the top-most side of the ball
        cue_ball_id:
            The ball ID of the ball being cued.
        specs:
            The cue specs.
        model_name:
            The name of the cue model directory under ``pooltool/models/cue/``.

            Important if rendering the cue in a scene.
    """

    id: str = field(default="cue_stick")
    V0: float = field(default=2.0)
    phi: float = field(default=0.0)
    theta: float = field(default=0.0)
    a: float = field(default=0.0)
    b: float = field(default=0.25)
    cue_ball_id: str = field(default="cue")
    specs: CueSpecs = field(factory=CueSpecs.default)
    model_name: str | None = field(default=None)

    def __repr__(self):
        lines = [
            f"<{self.__class__.__name__} object at {hex(id(self))}>",
            f" ├── V0    : {self.V0}",
            f" ├── phi   : {self.phi}",
            f" ├── a     : {self.a}",
            f" ├── b     : {self.b}",
            f" └── theta : {self.theta}",
        ]

        return "\n".join(lines) + "\n"

    def copy(self) -> Cue:
        """Create a copy

        Note:
            :attr:`specs` is shared between ``self`` and the copy, but that's ok because
            it's frozen and has no mutable attributes.
        """
        return evolve(self)

    def reset_state(self) -> None:
        """Resets :attr:`V0`, :attr:`phi`, :attr:`theta`, :attr:`a` and :attr:`b` to their defaults."""
        field_defaults = {
            fname: field.default
            for fname, field in fields_dict(self.__class__).items()
            if fname in ("V0", "phi", "theta", "a", "b")
        }
        self.set_state(**field_defaults)

    def set_state(
        self,
        V0: float | None = None,
        phi: float | None = None,
        theta: float | None = None,
        a: float | None = None,
        b: float | None = None,
        cue_ball_id: str | None = None,
    ) -> None:
        """Set the cueing parameters

        Args:
            V0: See :attr:`V0`
            phi: See :attr:`phi`
            theta: See :attr:`theta`
            a: See :attr:`a`
            b: See :attr:`b`
            cue_ball_id: See :attr:`cue_ball_id`

        If any arguments are ``None``, they will be left untouched--they will not be set
        to None.
        """
        if V0 is not None:
            self.V0 = V0
        if phi is not None:
            self.phi = phi
        if theta is not None:
            self.theta = theta
        if a is not None:
            self.a = a
        if b is not None:
            self.b = b
        if cue_ball_id is not None:
            self.cue_ball_id = cue_ball_id

    @classmethod
    def from_game_type(cls, game_type: GameType, id: str | None = None) -> Cue:
        if game_type not in _default_map:
            raise NotImplementedError(
                f"There is no cue stick associated with '{game_type}'"
            )

        if id is None:
            id = fields_dict(cls)["id"].default
            assert id is not None

        prebuilt = _default_map[game_type]
        cue = cls(id=id)
        cue.specs = CueSpecs.prebuilt(prebuilt)
        cue.model_name = CUE_MODELS[prebuilt]
        return cue

    @classmethod
    def default(cls) -> Cue:
        """Construct a cue with defaults"""
        return Cue()
