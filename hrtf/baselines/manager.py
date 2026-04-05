import json
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal

from hrtf.core.types import SignalSummary

@dataclass
class BaselineRecord:
    name: str
    captured_from_run: str
    captured_at: str
    scenario_hash: str
    robot_hash: str
    metrics: dict[str, SignalSummary]

@dataclass
class MetricDelta:
    signal: str
    metric: str
    baseline_value: float
    current_value: float
    absolute_delta: float
    percentage_delta: float
    regressed: bool

@dataclass
class RegressionReport:
    verdict: Literal["PASS", "REGRESSED"]
    baseline_name: str
    run_id: str
    per_metric: list[MetricDelta]
    tolerance: float

class BaselineManager:
    """Baseline capture, storage, and comparison."""

    def __init__(self, store_path: Path = Path(".hrtf/baselines")):
        self.store_path = store_path
        self.store_path.mkdir(parents=True, exist_ok=True)

    def _read_run_result(self, run_id: str, results_dir: Path = Path("results")) -> dict:
        run_file = results_dir / f"{run_id}.json"
        if not run_file.exists():
            raise FileNotFoundError(f"Run result not found: {run_file}")
        return json.loads(run_file.read_text())

    def capture(self, run_id: str, name: str, results_dir: Path = Path("results")) -> BaselineRecord:
        run_data = self._read_run_result(run_id, results_dir)

        metrics = {}
        for scenario in run_data.get("scenarios", []):
            for sig, summ in scenario.get("signal_summaries", {}).items():
                metrics[sig] = SignalSummary(**summ)

        record = BaselineRecord(
            name=name,
            captured_from_run=run_id,
            captured_at=datetime.now().isoformat(),
            scenario_hash=run_data.get("evidence_manifest", {}).get("scenario_yaml_hash", ""),
            robot_hash=run_data.get("evidence_manifest", {}).get("robot_urdf_hash", ""),
            metrics=metrics
        )

        baseline_dir = self.store_path / name
        baseline_dir.mkdir(parents=True, exist_ok=True)

        # We need a custom serializer for dataclasses
        class DCEncoder(json.JSONEncoder):
            def default(self, o):
                if hasattr(o, "__dataclass_fields__"):
                    return asdict(o)
                return super().default(o)

        with open(baseline_dir / "baseline.json", "w") as f:
            json.dump(record, f, cls=DCEncoder, indent=2)

        return record

    def compare(self, run_id: str, baseline_name: str, tolerance: float = 0.05, results_dir: Path = Path("results")) -> RegressionReport:
        baseline_file = self.store_path / baseline_name / "baseline.json"
        if not baseline_file.exists():
            raise FileNotFoundError(f"Baseline not found: {baseline_file}")

        baseline_data = json.loads(baseline_file.read_text())
        run_data = self._read_run_result(run_id, results_dir)

        current_metrics = {}
        for scenario in run_data.get("scenarios", []):
            for sig, summ in scenario.get("signal_summaries", {}).items():
                current_metrics[sig] = summ

        deltas = []
        overall_regressed = False

        for sig, base_summ in baseline_data.get("metrics", {}).items():
            curr_summ = current_metrics.get(sig)
            if not curr_summ:
                continue

            for metric_key in ["mean", "max", "min", "std", "final_value"]:
                b_val = base_summ.get(metric_key, 0.0)
                c_val = curr_summ.get(metric_key, 0.0)

                abs_delta = abs(c_val - b_val)
                pct_delta = (abs_delta / abs(b_val)) if b_val != 0 else (1.0 if abs_delta > 0 else 0.0)
                regressed = pct_delta > tolerance

                if regressed:
                    overall_regressed = True

                deltas.append(MetricDelta(
                    signal=sig,
                    metric=metric_key,
                    baseline_value=b_val,
                    current_value=c_val,
                    absolute_delta=abs_delta,
                    percentage_delta=pct_delta,
                    regressed=regressed
                ))

        return RegressionReport(
            verdict="REGRESSED" if overall_regressed else "PASS",
            baseline_name=baseline_name,
            run_id=run_id,
            per_metric=deltas,
            tolerance=tolerance
        )
