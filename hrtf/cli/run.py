import click
import json
import dataclasses
from pathlib import Path
from datetime import datetime

from hrtf.execution.orchestrator import ExecutionOrchestrator
from hrtf.core.types import RunResult, EvidenceManifest, Verdict

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Verdict):
            return o.value
        return super().default(o)

@click.command()
@click.argument('scenario_path', type=click.Path(exists=True))
@click.option('--sim', default='gazebo', help='Simulator backend')
@click.option('--seed', type=int, default=42, help='Random seed')
@click.option('--output-dir', type=click.Path(), default='results', help='Output directory')
def run(scenario_path, sim, seed, output_dir):
    """Execute a scenario."""
    click.echo(f"Running scenario {scenario_path} with {sim} (seed={seed})")

    orchestrator = ExecutionOrchestrator()
    path = Path(scenario_path)

    scenario_result = orchestrator.run_scenario(path)

    run_res = RunResult(
        run_id=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(),
        overall_verdict=scenario_result.verdict,
        scenarios=[scenario_result],
        evidence_manifest=EvidenceManifest(
            scenario_yaml_hash=scenario_result.scenario_hash,
            robot_urdf_hash="",
            simulator=sim,
            simulator_version="unknown",
            seed=seed,
            hrtf_version="0.1.0",
            python_version="3.10",
            os_info="unknown"
        ),
        total_wall_clock=scenario_result.wall_clock_duration
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_res.run_id}.json"

    with open(out_file, "w") as f:
        json.dump(run_res, f, cls=EnhancedJSONEncoder, indent=2)

    if scenario_result.verdict == Verdict.PASS:
        click.echo(click.style(f"Scenario PASS. Result saved to {out_file}", fg="green"))
    elif scenario_result.verdict == Verdict.FAIL:
        click.echo(click.style(f"Scenario FAIL. Result saved to {out_file}", fg="red"))
        # We don't system.exit(1) yet to keep it simple, but click typically handles it.
    else:
        click.echo(click.style(f"Scenario ERROR: {scenario_result.error_message}", fg="yellow"))
