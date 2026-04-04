import click

@click.command()
@click.argument('robot_urdf')
@click.option('--scenario-type', help='Scenario type (e.g., balance, gait)')
@click.option('--output', help='Output path for the generated template')
def init(robot_urdf, scenario_type, output):
    """Generate scenario template."""
    click.echo(f"Initializing scenario template for {robot_urdf}...")
