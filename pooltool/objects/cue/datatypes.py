#! /usr/bin/env python

from __future__ import annotations

from typing import Optional

from attrs import define, evolve, field, fields_dict


@define(frozen=True)
class CueSpecs:
    """Cue stick specifications

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
        butt_radius:
            The butt radius.
        end_mass:
            The mass of the of the cue's end. This controls the amount of deflection
            (squirt) that occurs when using sidespin. Lower means less deflection. It is
            defined here:
            https://billiards.colostate.edu/technical_proofs/new/TP_A-31.pdf.
    """

    brand: str = field(default="Predator")
    M: float = field(default=0.567)
    length: float = field(default=1.4732)
    tip_radius: float = field(default=0.007)
    butt_radius: float = field(default=0.02)
    end_mass: float = field(default=0.170097 / 30)

    @staticmethod
    def default() -> CueSpecs:
        """Construct a default cue spec"""
        return CueSpecs()

    @staticmethod
    def snooker() -> CueSpecs:
        raise NotImplementedError()


@define
class Cue:
    """A cue stick

    Attributes:
        id:
            An ID for the cue.
        V0:
            The impact speed.

            Units are *m/s*.

            Warning: This is the speed of the cue stick upon impact, not the speed of the
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
    """

    id: str = field(default="cue_stick")
    V0: float = field(default=2.0)
    phi: float = field(default=0.0)
    theta: float = field(default=0.0)
    a: float = field(default=0.0)
    b: float = field(default=0.25)
    cue_ball_id: str = field(default="cue")
    specs: CueSpecs = field(factory=CueSpecs.default)

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
        V0: Optional[float] = None,
        phi: Optional[float] = None,
        theta: Optional[float] = None,
        a: Optional[float] = None,
        b: Optional[float] = None,
        cue_ball_id: Optional[str] = None,
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
    def default(cls) -> Cue:
        """Construct a cue with defaults"""
        return Cue()
