import sys
import platform
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


from hrtf.scenario.composer import compose

@click.command()
@click.argument('scenario_path', type=click.Path(exists=True), required=False)
@click.option('--fixture', type=click.Path(exists=True), help='Path to fixture YAML')
@click.option('--test-case', type=click.Path(exists=True), help='Path to test case YAML')
@click.option('--run-settings', type=click.Path(exists=True), help='Path to run settings YAML')
@click.option('--sim', default=None, help='Simulator backend (overrides scenario YAML)')
@click.option('--seed', type=int, default=None, help='Random seed (overrides scenario YAML)')
@click.option('--output-dir', type=click.Path(), default='results', help='Output directory')
@click.option('--param', '-p', multiple=True, help='Parameter override in key=value format (e.g. -p duration=10.0)')
def run(scenario_path, fixture, test_case, run_settings, sim, seed, output_dir, param):
    """Execute a scenario (monolithic or composed)."""
    # Build parameter overrides from CLI flags
    overrides = {}
    if sim:
        overrides["simulator.backend"] = sim
    if seed is not None:
        overrides["simulator.seed"] = str(seed)
    for p in param:
        if "=" in p:
            key, value = p.split("=", 1)
            overrides[key] = value

    orchestrator = ExecutionOrchestrator()
    scenario_result = None

    if fixture and test_case and run_settings:
        click.echo(f"Running composed scenario from {fixture}, {test_case}, {run_settings}")
        config = compose(Path(fixture), Path(test_case), Path(run_settings), param_overrides=overrides if overrides else None)
        scenario_result = orchestrator.run_composed(config)
    elif scenario_path:
        path = Path(scenario_path)
        click.echo(f"Running scenario: {path.name}")
        scenario_result = orchestrator.run_scenario(path, param_overrides=overrides if overrides else None)
    else:
        click.echo(click.style("ERROR: Must provide either scenario_path or all of --fixture, --test-case, and --run-settings.", fg="red", bold=True))
        sys.exit(3)

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_res = RunResult(
        run_id=run_id,
        timestamp=datetime.now(),
        overall_verdict=scenario_result.verdict,
        scenarios=[scenario_result],
        evidence_manifest=EvidenceManifest(
            scenario_yaml_hash=scenario_result.scenario_hash,
            robot_urdf_hash="",
            simulator=sim or "from_scenario",
            simulator_version="unknown",
            seed=seed or 0,
            hrtf_version="0.1.0",
            python_version=platform.python_version(),
            os_info=platform.platform()
        ),
        total_wall_clock=scenario_result.wall_clock_duration
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_id}.json"

    with open(out_file, "w") as f:
        json.dump(run_res, f, cls=EnhancedJSONEncoder, indent=2)

    # Display assertion results
    for a in scenario_result.assertion_results:
        icon = "PASS" if a.verdict == Verdict.PASS else "FAIL"
        msg = f"  [{icon}] {a.assertion_type} on {a.signal_name}"
        if a.verdict != Verdict.PASS and a.violation_value is not None:
            msg += f" (got {a.violation_value:.4f}, expected bound {a.expected_bound})"
        color = "green" if a.verdict == Verdict.PASS else "red"
        click.echo(click.style(msg, fg=color))

    click.echo(f"Result saved to {out_file}")

    # Exit non-zero on failure or error (RP-03)
    if scenario_result.verdict == Verdict.PASS:
        click.echo(click.style(f"PASSED", fg="green", bold=True))
    elif scenario_result.verdict == Verdict.FAIL:
        click.echo(click.style(f"FAILED", fg="red", bold=True))
        sys.exit(1)
    else:
        click.echo(click.style(f"ERROR: {scenario_result.error_message}", fg="yellow", bold=True))
        sys.exit(2)
