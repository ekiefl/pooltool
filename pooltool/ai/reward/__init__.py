from pooltool.ai.reward.minimal import RewardMinimal
from pooltool.ai.reward.point_based import RewardPointBased

DEFAULT_REWARD = RewardMinimal()


__all__ = [
    "RewardPointBased",
    "RewardMinimal",
]
