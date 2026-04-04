import click

@click.command()
@click.argument('scenario', required=False)
@click.option('--suite', help='Execute a named test suite')
@click.option('--sim', type=click.Choice(['gazebo', 'mujoco', 'isaac']), help='Simulation back-end')
@click.option('--seed', type=int, help='Random seed for determinism')
@click.option('--workers', type=int, help='Number of parallel workers')
@click.option('--output-dir', help='Directory to store results')
@click.option('--param', multiple=True, help='Parameter overrides (key=value)')
def run(scenario, suite, sim, seed, workers, output_dir, param):
    """Execute one or more scenarios or a test suite."""
    click.echo("Running scenarios...")
