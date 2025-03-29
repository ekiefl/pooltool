import numpy as np
from trajectory import TrajectoryDatum


def calculate_vector_loss(
    reference_data: list[TrajectoryDatum],
    trial_data: list[TrajectoryDatum],
    alpha: float = 0.5,
):
    error_sum = 0
    dir_error_sum = 0
    mag_error_sum = 0

    for ref, trial in zip(reference_data, trial_data, strict=True):
        if ref.norm < 0.01 or trial.norm < 0.01:
            continue

        dir_error = 1 - np.dot(ref.unit, trial.unit)
        mag_error = np.abs(ref.norm - trial.norm) / ref.norm
        combined_error = alpha * dir_error + (1 - alpha) * mag_error

        error_sum += combined_error
        dir_error_sum += dir_error
        mag_error_sum += mag_error

    return error_sum
