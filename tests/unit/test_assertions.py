import pytest
import numpy as np
from hrtf.assertions.predicates import AlwaysAbove, NeverExceeds, ReachesWithin, StabilisesWithin
from hrtf.core.types import Verdict

def test_always_above_pass():
    # Signal [timestamp, value]
    signal = np.array([
        [0.0, 1.0],
        [1.0, 1.5],
        [2.0, 1.2],
        [3.0, 2.0]
    ])

    assertion = AlwaysAbove(value=0.5, window=(0.0, 3.0))
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.PASS
    assert result.assertion_type == "always_above"
    assert result.signal_name == "test_signal"

def test_always_above_fail():
    signal = np.array([
        [0.0, 1.0],
        [1.0, 0.2],  # Drops below 0.5
        [2.0, 1.2],
        [3.0, 2.0]
    ])

    assertion = AlwaysAbove(value=0.5, window=(0.0, 3.0))
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.FAIL
    assert result.first_violation_time == 1.0
    assert result.violation_value == 0.2
    assert result.expected_bound == 0.5

def test_never_exceeds_pass():
    signal = np.array([
        [0.0, 10.0],
        [1.0, 15.0],
        [2.0, 12.0],
        [3.0, 20.0]
    ])

    assertion = NeverExceeds(value=25.0, window=(0.0, 3.0))
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.PASS
    assert result.assertion_type == "never_exceeds"

def test_never_exceeds_fail():
    signal = np.array([
        [0.0, 10.0],
        [1.0, 15.0],
        [2.0, 30.0],  # Exceeds 25.0
        [3.0, 20.0]
    ])

    assertion = NeverExceeds(value=25.0, window=(0.0, 3.0))
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.FAIL
    assert result.first_violation_time == 2.0
    assert result.violation_value == 30.0
    assert result.expected_bound == 25.0

def test_reaches_within_pass():
    signal = np.array([
        [0.0, 1.0],
        [1.0, 1.5],
        [2.0, 1.98],
        [3.0, 2.0]
    ])

    assertion = ReachesWithin(value=2.0, window=(0.0, 3.0), tolerance=0.05)
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.PASS

def test_reaches_within_fail():
    signal = np.array([
        [0.0, 1.0],
        [1.0, 1.5],
        [2.0, 1.8],
        [3.0, 1.8]
    ])

    assertion = ReachesWithin(value=2.0, window=(0.0, 3.0), tolerance=0.05)
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.FAIL

def test_stabilises_within_pass():
    signal = np.array([
        [0.0, 1.0],
        [1.0, 1.5],
        [2.0, 1.51],
        [2.5, 1.50],
        [3.0, 1.52]
    ])

    # tolerance of 0.1 -> var < 0.01. The last 3 points have var ~= 0.00006
    assertion = StabilisesWithin(tolerance=0.1, window=(0.0, 3.0), moving_window_size=1.0)
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.PASS

def test_stabilises_within_fail():
    signal = np.array([
        [0.0, 1.0],
        [1.0, 2.0],
        [2.0, 0.0],
        [2.5, 2.0],
        [3.0, 0.0]
    ])

    assertion = StabilisesWithin(tolerance=0.1, window=(0.0, 3.0), moving_window_size=1.0)
    result = assertion.evaluate(signal, "test_signal")

    assert result.verdict == Verdict.FAIL
