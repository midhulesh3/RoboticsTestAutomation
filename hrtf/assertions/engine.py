from hrtf.core.types import AssertionSpec, AssertionResult, Verdict
from hrtf.signals.logger import SignalLog
from hrtf.assertions.predicates import AlwaysAbove, NeverExceeds, ReachesWithin, StabilisesWithin
from hrtf.assertions.compound import CompoundAssertion

class AssertionEngine:
    """Evaluates a set of assertions against recorded signal data."""

    def evaluate(self, log: SignalLog, specs: list[AssertionSpec]) -> list[AssertionResult]:
        results = []
        for spec in specs:
            signal_data = log.get_signal(spec.signal) if spec.signal else []

            if spec.type == "always_above":
                if spec.value is None or spec.window is None:
                    results.append(AssertionResult(verdict=Verdict.ERROR, assertion_type=spec.type, signal_name=spec.signal or "unknown"))
                    continue
                predicate = AlwaysAbove(value=spec.value, window=spec.window)
                res = predicate.evaluate(signal_data, spec.signal)
                results.append(res)

            elif spec.type == "never_exceeds":
                if spec.value is None or spec.window is None:
                    results.append(AssertionResult(verdict=Verdict.ERROR, assertion_type=spec.type, signal_name=spec.signal or "unknown"))
                    continue
                predicate = NeverExceeds(value=spec.value, window=spec.window)
                res = predicate.evaluate(signal_data, spec.signal)
                results.append(res)

            elif spec.type == "reaches_within":
                if spec.value is None or spec.window is None:
                    results.append(AssertionResult(verdict=Verdict.ERROR, assertion_type=spec.type, signal_name=spec.signal or "unknown"))
                    continue
                tol = spec.tolerance if spec.tolerance is not None else 0.05
                predicate = ReachesWithin(value=spec.value, window=spec.window, tolerance=tol)
                res = predicate.evaluate(signal_data, spec.signal)
                results.append(res)

            elif spec.type == "stabilises_within":
                if spec.tolerance is None or spec.window is None:
                    results.append(AssertionResult(verdict=Verdict.ERROR, assertion_type=spec.type, signal_name=spec.signal or "unknown"))
                    continue
                predicate = StabilisesWithin(tolerance=spec.tolerance, window=spec.window)
                res = predicate.evaluate(signal_data, spec.signal)
                results.append(res)

            elif spec.type == "compound":
                if spec.operator is None or spec.children is None:
                    results.append(AssertionResult(verdict=Verdict.ERROR, assertion_type=spec.type, signal_name=spec.signal or "unknown"))
                    continue

                child_predicates = []
                for child_spec in spec.children:
                    if child_spec.type == "always_above":
                        child_predicates.append(AlwaysAbove(child_spec.value, child_spec.window))
                    elif child_spec.type == "never_exceeds":
                        child_predicates.append(NeverExceeds(child_spec.value, child_spec.window))
                    elif child_spec.type == "reaches_within":
                        tol = child_spec.tolerance if child_spec.tolerance is not None else 0.05
                        child_predicates.append(ReachesWithin(child_spec.value, child_spec.window, tol))
                    elif child_spec.type == "stabilises_within":
                        child_predicates.append(StabilisesWithin(child_spec.tolerance, child_spec.window))

                predicate = CompoundAssertion(operator=spec.operator, children=child_predicates)
                res = predicate.evaluate(signal_data, spec.signal)
                results.append(res)

            else:
                # Unknown assertion type
                results.append(AssertionResult(
                    verdict=Verdict.ERROR,
                    assertion_type=spec.type,
                    signal_name=spec.signal or "unknown"
                ))

        return results
