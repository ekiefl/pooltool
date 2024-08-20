from __future__ import annotations

from functools import partial
from typing import Any, Dict, Optional, Tuple, Type, Union

from attrs import define, evolve, field
from cattrs.converters import Converter

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.datatypes import NullObject
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.serialize import SerializeFormat, conversion
from pooltool.utils import strenum


class EventType(strenum.StrEnum):
    """An Enum of event types

    Attributes:
        NONE:
            The null event.
        BALL_BALL:
            A ball-ball collision.
        BALL_LINEAR_CUSHION:
            A ball collision with a linear cushion segment.
        BALL_CIRCULAR_CUSHION:
            A ball collision with a circular cushion segment.
        BALL_POCKET:
            A ball pocket "collision". This marks the point at which the ball crosses
            the *point of no return*.
        STICK_BALL:
            A cue-stick ball collision.
        SPINNING_STATIONARY:
            A ball transition from spinning to stationary.
        ROLLING_STATIONARY:
            A ball transition from rolling to stationary.
        ROLLING_SPINNING:
            A ball transition from rolling to spinning.
        SLIDING_ROLLING:
            A ball transition from sliding to rolling.
    """

    NONE = strenum.auto()
    BALL_BALL = strenum.auto()
    BALL_LINEAR_CUSHION = strenum.auto()
    BALL_CIRCULAR_CUSHION = strenum.auto()
    BALL_POCKET = strenum.auto()
    STICK_BALL = strenum.auto()
    SPINNING_STATIONARY = strenum.auto()
    ROLLING_STATIONARY = strenum.auto()
    ROLLING_SPINNING = strenum.auto()
    SLIDING_ROLLING = strenum.auto()

    def is_collision(self) -> bool:
        """Returns whether the member is a collision"""
        return self in {
            EventType.BALL_BALL,
            EventType.BALL_CIRCULAR_CUSHION,
            EventType.BALL_LINEAR_CUSHION,
            EventType.BALL_POCKET,
            EventType.STICK_BALL,
        }

    def is_transition(self) -> bool:
        """Returns whether the member is a transition"""
        return self in {
            EventType.SPINNING_STATIONARY,
            EventType.ROLLING_STATIONARY,
            EventType.ROLLING_SPINNING,
            EventType.SLIDING_ROLLING,
        }


Object = Union[
    NullObject,
    Cue,
    Ball,
    Pocket,
    LinearCushionSegment,
    CircularCushionSegment,
]


class AgentType(strenum.StrEnum):
    """An Enum of event agents

    Attributes:
        NULL: A null agent.
        CUE: A cue stick agent.
        BALL: A ball agent.
        POCKET: A pocket agent.
        LINEAR_CUSHION_SEGMENT: A linear cushion segment agent.
        CIRCULAR_CUSHION_SEGMENT: A circular cushion segment agent.
    """

    NULL = strenum.auto()
    CUE = strenum.auto()
    BALL = strenum.auto()
    POCKET = strenum.auto()
    LINEAR_CUSHION_SEGMENT = strenum.auto()
    CIRCULAR_CUSHION_SEGMENT = strenum.auto()


_class_to_type: Dict[Type[Object], AgentType] = {
    NullObject: AgentType.NULL,
    Cue: AgentType.CUE,
    Ball: AgentType.BALL,
    Pocket: AgentType.POCKET,
    LinearCushionSegment: AgentType.LINEAR_CUSHION_SEGMENT,
    CircularCushionSegment: AgentType.CIRCULAR_CUSHION_SEGMENT,
}

_type_to_class = {v: k for k, v in _class_to_type.items()}


@define
class Agent:
    """An event agent.

    This class represents an agent involved in events. The agent can be in
    different states before and after an event, represented by ``initial`` and
    ``final`` states.

    Attributes:
        id: ID for the agent.
        agent_type: The type of the agent.
        initial: The state of the agent before an event.
        final: The state of the agent after an event.
    """

    id: str
    agent_type: AgentType

    initial: Optional[Object] = field(default=None)
    final: Optional[Object] = field(default=None)

    def set_initial(self, obj: Object) -> None:
        """Sets the initial state of the agent (before event resolution).

        This makes a copy of the passed object and sets it to :attr:`initial`.

        In the case of a :attr:`AgentType.BALL` agent type, it drops history fields
        before copying to save time and memory.

        Args:
            obj:
                The object from which :attr:`initial` will be set.
        """
        if self.agent_type == AgentType.NULL:
            return

        if self.agent_type == AgentType.BALL:
            # In this special case, we drop history fields prior to copying because they
            # are potentially huge and copying them is expensive
            assert isinstance(obj, Ball)
            self.initial = obj.copy(drop_history=True)
        else:
            self.initial = obj.copy()

    def set_final(self, obj: Object) -> None:
        """Sets the final state of the agent (after event resolution).

        This makes a copy of the passed object and sets it to :attr:`final`.

        In the case of a :attr:`AgentType.BALL` agent type, it drops history fields
        before copying to save time and memory.

        Args:
            obj:
                The object from which :attr:`final` will be set.
        """
        if self.agent_type == AgentType.NULL:
            return

        if self.agent_type == AgentType.BALL:
            # In this special case, we drop history fields prior to copying because they
            # are potentially huge and copying them is expensive
            assert isinstance(obj, Ball)
            self.final = obj.copy(drop_history=True)
        else:
            self.final = obj.copy()

    def matches(self, obj: Object) -> bool:
        """Determines if the given object matches the agent.

        It checks if the object is of the correct class type and if the IDs match.

        Args:
            obj: The object to compare with the agent.

        Returns:
            bool:
                True if the object's class type and ID match the agent's type and ID,
                False otherwise.
        """
        correct_class = _class_to_type[type(obj)] == self.agent_type
        return correct_class and obj.id == self.id

    @staticmethod
    def from_object(obj: Object, set_initial: bool = False) -> Agent:
        """Creates an agent instance from an object.

        Optionally sets the initial state of the agent based on the provided object. The
        final state is not set.

        Args:
            obj:
                The object to create the agent from.
            set_initial:
                If True, sets the initial state of the agent to the object's state.

        Returns:
            Agent: A new instance of Agent.
        """
        agent = Agent(id=obj.id, agent_type=_class_to_type[type(obj)])

        if set_initial:
            agent.set_initial(obj)

        return agent

    def copy(self) -> Agent:
        """Create a copy."""
        return evolve(self)


def _disambiguate_agent_structuring(
    uo: Dict[str, Any], _: Type[Agent], con: Converter
) -> Agent:
    id = con.structure(uo["id"], str)
    agent_type = con.structure(uo["agent_type"], AgentType)

    # All agents but the NULL agent have initial states
    if agent_type == AgentType.NULL:
        initial = None
    else:
        initial = con.structure(uo["initial"], _type_to_class[agent_type])

    # Only BALL and POCKET have final states
    if agent_type in (AgentType.BALL, AgentType.POCKET):
        final = con.structure(uo["final"], _type_to_class[agent_type])
    else:
        final = None

    return Agent(
        id=id,
        agent_type=agent_type,
        initial=initial,  # type: ignore
        final=final,  # type: ignore
    )


conversion.register_structure_hook(
    cl=Agent,
    func=partial(
        _disambiguate_agent_structuring,
        con=conversion[SerializeFormat.JSON],
    ),
    which=(SerializeFormat.JSON,),
)
conversion.register_structure_hook(
    cl=Agent,
    func=partial(
        _disambiguate_agent_structuring,
        con=conversion[SerializeFormat.MSGPACK],
    ),
    which=(SerializeFormat.MSGPACK,),
)


@define
class Event:
    """Represents an event.

    This class models an event characterized by its type, the agents involved, and the
    time at which the event occurs.

    Agent states before and after event resolution are stored in the
    :attr:`Agent.initial` and :attr:`Agent.final` attributes of agents within
    :attr:`agents`.

    Attributes:
        event_type:
            The type of the event, indicating the nature of the event.
        agents:
            A tuple containing one or two agents involved in the event.

            Events that are collisions (:meth:`EventType.is_collision`) have two agents,
            while events that are transitions (:meth:`EventType.is_transition`), or
            events with event type :attr:`EventType.NONE`, have one agent.

            By convention, the order of the agents matches how the :class:`EventType`
            attributes are named.
        time:
            The time at which the event occurs.
    """

    event_type: EventType
    agents: Tuple[Agent, ...]
    time: float

    def __repr__(self):
        lines = [
            f"<{self.__class__.__name__} object at {hex(id(self))}>",
            f" ├── type   : {self.event_type}",
            f" ├── time   : {self.time}",
            f" └── agents : {self.ids}",
        ]
        return "\n".join(lines) + "\n"

    @property
    def ids(self) -> Tuple[str, ...]:
        """Retrieves the IDs of the agents involved in the event.

        This property provides access to a tuple of agent IDs, allowing identification
        of the agents involved in the event.

        Returns:
            Tuple[str, ...]: A tuple containing the IDs of the agents involved in the event.
        """
        return tuple(agent.id for agent in self.agents)  # type: ignore

    def copy(self) -> Event:
        """Create a copy."""
        # NOTE is this deep-ish copy?
        return evolve(self)
