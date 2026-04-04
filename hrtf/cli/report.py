import click

@click.command()
@click.argument('run_id')
@click.option('--format', type=click.Choice(['json', 'html', 'pdf', 'sarif']), help='Report format')
@click.option('--output', help='Output path')
def report(run_id, format, output):
    """Generate reports."""
    click.echo(f"Generating {format} report for run '{run_id}'...")
