import click
from pathlib import Path
from hrtf.baselines.manager import BaselineManager

@click.group()
def baseline():
    """Baseline capture and comparison commands."""
    pass

@baseline.command()
@click.argument('run_id')
@click.argument('name')
@click.option('--store', help='Path to baseline store')
def capture(run_id, name, store):
    """Capture baseline from run."""
    store_path = Path(store) if store else Path(".hrtf/baselines")
    manager = BaselineManager(store_path=store_path)

    try:
        record = manager.capture(run_id, name)
        click.echo(click.style(f"Successfully captured baseline '{name}' from run '{run_id}'", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error capturing baseline: {e}", fg="red"))

@baseline.command()
@click.argument('run_id')
@click.argument('baseline_name')
@click.option('--tolerance', type=float, default=0.05, help='Comparison tolerance (default: 0.05)')
@click.option('--format', type=click.Choice(['json', 'table']), default='table', help='Output format')
def compare(run_id, baseline_name, tolerance, format):
    """Compare run to baseline."""
    manager = BaselineManager()
    try:
        report = manager.compare(run_id, baseline_name, tolerance)

        if report.verdict == "PASS":
            click.echo(click.style(f"Run '{run_id}' passes against baseline '{baseline_name}'", fg="green"))
        else:
            click.echo(click.style(f"Run '{run_id}' REGRESSED against baseline '{baseline_name}'", fg="red"))

        for delta in report.per_metric:
            if delta.regressed:
                click.echo(f"  - {delta.signal} ({delta.metric}): {delta.baseline_value:.4f} -> {delta.current_value:.4f} ({delta.percentage_delta*100:.1f}% change)")

    except Exception as e:
        click.echo(click.style(f"Error comparing baseline: {e}", fg="red"))

@baseline.command()
@click.option('--store', help='Path to baseline store')
def list(store):
    """List stored baselines."""
    store_path = Path(store) if store else Path(".hrtf/baselines")
    if not store_path.exists():
        click.echo("No baselines stored.")
        return

    baselines = [d.name for d in store_path.iterdir() if d.is_dir()]
    if not baselines:
        click.echo("No baselines stored.")
    else:
        click.echo("Stored baselines:")
        for b in baselines:
            click.echo(f"  - {b}")