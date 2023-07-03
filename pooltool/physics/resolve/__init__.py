from __future__ import annotations

import attrs


@attrs.define
class Resolver:
    # TODO This class will manage the physics strategies used for each event type
    placeholder: str = attrs.field(default="dummy")

    @classmethod
    def default(cls) -> Resolver:
        return cls()
