import numpy as np
from hrtf.core.types import AssertionResult, Verdict
from hrtf.assertions.predicates import AssertionPredicate

class CompoundAssertion(AssertionPredicate):
    """AND/OR combination of multiple predicates."""

    def __init__(self, operator: str, children: list[AssertionPredicate]):
        self.operator = operator.lower()
        if self.operator not in ["and", "or"]:
            raise ValueError(f"Unknown compound operator: {operator}")
        self.children = children

    def evaluate(self, signal: np.ndarray, signal_name: str) -> AssertionResult:
        # For compound assertions, the engine will usually pass a dictionary of signals.
        # But for MVP, let's assume they evaluate against a single signal or handle evaluation inside the engine instead.
        # Given the interface expects a single signal and signal_name, we will evaluate children on the same signal for now.

        results = []
        for child in self.children:
            results.append(child.evaluate(signal, signal_name))

        if self.operator == "and":
            passed = all(r.verdict == Verdict.PASS for r in results)
        else:  # or
            passed = any(r.verdict == Verdict.PASS for r in results)

        return AssertionResult(
            verdict=Verdict.PASS if passed else Verdict.FAIL,
            assertion_type=f"compound_{self.operator}",
            signal_name=signal_name,
            expected_bound=0.0  # Placeholder since we have multiple bounds
        )
