from abc import ABC, abstractmethod
import numpy as np
from hrtf.core.types import AssertionResult, Verdict, SignalSummary

class AssertionPredicate(ABC):
    """Base class for all signal assertions."""

    @abstractmethod
    def evaluate(self, signal: np.ndarray, signal_name: str) -> AssertionResult:
        """Evaluate the predicate against signal data."""
        ...

def _get_summary(signal: np.ndarray) -> SignalSummary | None:
    if len(signal) == 0:
        return None
    values = signal[:, 1]
    return SignalSummary(
        mean=float(np.mean(values)),
        min=float(np.min(values)),
        max=float(np.max(values)),
        std=float(np.std(values)),
        final_value=float(values[-1]),
        sample_count=len(values)
    )

class AlwaysAbove(AssertionPredicate):
    """Signal must remain above threshold for entire window."""

    def __init__(self, value: float, window: tuple[float, float]):
        self.value = value
        self.window = window

    def evaluate(self, signal: np.ndarray, signal_name: str) -> AssertionResult:
        if len(signal) == 0:
            return AssertionResult(
                verdict=Verdict.FAIL,
                assertion_type="always_above",
                signal_name=signal_name,
                expected_bound=self.value
            )

        windowed = signal[
            (signal[:, 0] >= self.window[0]) &
            (signal[:, 0] <= self.window[1])
        ]

        summary = _get_summary(signal)

        if len(windowed) == 0:
            return AssertionResult(
                verdict=Verdict.PASS, # Or skipped
                assertion_type="always_above",
                signal_name=signal_name,
                signal_summary=summary
            )

        violations = windowed[windowed[:, 1] < self.value]

        if len(violations) == 0:
            return AssertionResult(
                verdict=Verdict.PASS,
                assertion_type="always_above",
                signal_name=signal_name,
                signal_summary=summary
            )

        return AssertionResult(
            verdict=Verdict.FAIL,
            assertion_type="always_above",
            signal_name=signal_name,
            first_violation_time=float(violations[0, 0]),
            violation_value=float(violations[0, 1]),
            expected_bound=self.value,
            violation_duration=float(violations[-1, 0] - violations[0, 0]),
            signal_summary=summary
        )

class ReachesWithin(AssertionPredicate):
    """Signal must reach target value within tolerance before the end of the window."""

    def __init__(self, value: float, window: tuple[float, float], tolerance: float = 0.05):
        self.value = value
        self.window = window
        self.tolerance = tolerance

    def evaluate(self, signal: np.ndarray, signal_name: str) -> AssertionResult:
        if len(signal) == 0:
            return AssertionResult(
                verdict=Verdict.FAIL,
                assertion_type="reaches_within",
                signal_name=signal_name,
                expected_bound=self.value
            )

        windowed = signal[
            (signal[:, 0] >= self.window[0]) &
            (signal[:, 0] <= self.window[1])
        ]

        summary = _get_summary(signal)

        if len(windowed) == 0:
            return AssertionResult(
                verdict=Verdict.FAIL,
                assertion_type="reaches_within",
                signal_name=signal_name,
                signal_summary=summary
            )

        # Check if any value in the window is within [value - tolerance, value + tolerance]
        reached = windowed[
            (windowed[:, 1] >= self.value - self.tolerance) &
            (windowed[:, 1] <= self.value + self.tolerance)
        ]

        if len(reached) > 0:
            return AssertionResult(
                verdict=Verdict.PASS,
                assertion_type="reaches_within",
                signal_name=signal_name,
                signal_summary=summary
            )

        return AssertionResult(
            verdict=Verdict.FAIL,
            assertion_type="reaches_within",
            signal_name=signal_name,
            expected_bound=self.value,
            signal_summary=summary
        )

class StabilisesWithin(AssertionPredicate):
    """Signal variance must fall below tolerance^2 within the specified window."""

    def __init__(self, tolerance: float, window: tuple[float, float], moving_window_size: float = 1.0):
        self.tolerance = tolerance
        self.window = window
        self.moving_window_size = moving_window_size

    def evaluate(self, signal: np.ndarray, signal_name: str) -> AssertionResult:
        if len(signal) == 0:
            return AssertionResult(
                verdict=Verdict.FAIL,
                assertion_type="stabilises_within",
                signal_name=signal_name,
                expected_bound=self.tolerance
            )

        windowed = signal[
            (signal[:, 0] >= self.window[0]) &
            (signal[:, 0] <= self.window[1])
        ]

        summary = _get_summary(signal)

        if len(windowed) == 0:
            return AssertionResult(
                verdict=Verdict.FAIL,
                assertion_type="stabilises_within",
                signal_name=signal_name,
                signal_summary=summary
            )

        # We need to find if there is any point t in the window such that
        # the variance of the signal in [t, t + moving_window_size] is < tolerance^2
        variance_threshold = self.tolerance ** 2

        # Discretize the check by iterating over points in the window
        # For simplicity, we check the variance of the trailing `moving_window_size` at each point
        stabilised = False
        stabilisation_time = None

        for i, (t, val) in enumerate(windowed):
            sub_window = windowed[
                (windowed[:, 0] >= t - self.moving_window_size) &
                (windowed[:, 0] <= t)
            ]
            if len(sub_window) > 1: # Need at least 2 points for a meaningful variance
                var = np.var(sub_window[:, 1])
                if var < variance_threshold:
                    stabilised = True
                    stabilisation_time = t
                    break

        if stabilised:
            return AssertionResult(
                verdict=Verdict.PASS,
                assertion_type="stabilises_within",
                signal_name=signal_name,
                signal_summary=summary
            )

        return AssertionResult(
            verdict=Verdict.FAIL,
            assertion_type="stabilises_within",
            signal_name=signal_name,
            expected_bound=self.tolerance,
            signal_summary=summary
        )

class NeverExceeds(AssertionPredicate):
    """Signal must not exceed threshold at any point in window."""

    def __init__(self, value: float, window: tuple[float, float]):
        self.value = value
        self.window = window

    def evaluate(self, signal: np.ndarray, signal_name: str) -> AssertionResult:
        if len(signal) == 0:
            return AssertionResult(
                verdict=Verdict.PASS,
                assertion_type="never_exceeds",
                signal_name=signal_name,
                expected_bound=self.value
            )

        windowed = signal[
            (signal[:, 0] >= self.window[0]) &
            (signal[:, 0] <= self.window[1])
        ]

        summary = _get_summary(signal)

        if len(windowed) == 0:
            return AssertionResult(
                verdict=Verdict.PASS,
                assertion_type="never_exceeds",
                signal_name=signal_name,
                signal_summary=summary
            )

        violations = windowed[windowed[:, 1] > self.value]

        if len(violations) == 0:
            return AssertionResult(
                verdict=Verdict.PASS,
                assertion_type="never_exceeds",
                signal_name=signal_name,
                signal_summary=summary
            )

        return AssertionResult(
            verdict=Verdict.FAIL,
            assertion_type="never_exceeds",
            signal_name=signal_name,
            first_violation_time=float(violations[0, 0]),
            violation_value=float(violations[0, 1]),
            expected_bound=self.value,
            violation_duration=float(violations[-1, 0] - violations[0, 0]),
            signal_summary=summary
        )
