import click

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
    click.echo(f"Capturing baseline '{name}' from run '{run_id}'...")

@baseline.command()
@click.argument('run_id')
@click.argument('baseline_name')
@click.option('--tolerance', type=float, help='Comparison tolerance')
@click.option('--format', type=click.Choice(['json', 'table']), help='Output format')
def compare(run_id, baseline_name, tolerance, format):
    """Compare run to baseline."""
    click.echo(f"Comparing run '{run_id}' to baseline '{baseline_name}'...")

@baseline.command()
@click.option('--store', help='Path to baseline store')
def list(store):
    """List stored baselines."""
    click.echo("Listing baselines...")