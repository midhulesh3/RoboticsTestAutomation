import pytest
import numpy as np
from hrtf.assertions.predicates import AlwaysAbove, NeverExceeds
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
