import pytest
import json
from pathlib import Path
from datetime import datetime
from hrtf.baselines.manager import BaselineManager

def test_baseline_manager(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    store_dir = tmp_path / ".hrtf" / "baselines"
    manager = BaselineManager(store_path=store_dir)

    # Create fake run result
    run_id = "run_test_123"
    run_data = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "overall_verdict": "PASS",
        "evidence_manifest": {"scenario_yaml_hash": "abc", "robot_urdf_hash": "def"},
        "scenarios": [
            {
                "scenario_name": "test",
                "signal_summaries": {
                    "/test_signal": {
                        "mean": 1.0,
                        "min": 0.5,
                        "max": 1.5,
                        "std": 0.1,
                        "final_value": 1.2,
                        "sample_count": 100
                    }
                }
            }
        ]
    }

    with open(results_dir / f"{run_id}.json", "w") as f:
        json.dump(run_data, f)

    # Test capture
    record = manager.capture(run_id, "stable_baseline", results_dir=results_dir)
    assert record.name == "stable_baseline"
    assert "/test_signal" in record.metrics
    assert record.metrics["/test_signal"].mean == 1.0

    # Test compare - PASS
    report = manager.compare(run_id, "stable_baseline", tolerance=0.05, results_dir=results_dir)
    assert report.verdict == "PASS"
    assert len(report.per_metric) > 0

    # Test compare - REGRESSED
    # Modify run data slightly to cause regression
    run_data["scenarios"][0]["signal_summaries"]["/test_signal"]["mean"] = 1.2 # 20% diff
    run_id_2 = "run_test_456"
    with open(results_dir / f"{run_id_2}.json", "w") as f:
        json.dump(run_data, f)

    report = manager.compare(run_id_2, "stable_baseline", tolerance=0.05, results_dir=results_dir)
    assert report.verdict == "REGRESSED"
    assert any(m.regressed for m in report.per_metric)
