from pooltool.utils.strenum import StrEnum, auto


class GameType(StrEnum):
    """An Enum for supported game types

    Attributes:
        EIGHTBALL:
        NINEBALL:
        THREECUSHION:
        SNOOKER:
        SANDBOX:
        SUMTOTHREE:
    """

    EIGHTBALL = auto()
    NINEBALL = auto()
    THREECUSHION = auto()
    SNOOKER = auto()
    SANDBOX = auto()
    SUMTOTHREE = auto()
