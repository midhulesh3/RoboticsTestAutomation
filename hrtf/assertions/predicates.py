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
