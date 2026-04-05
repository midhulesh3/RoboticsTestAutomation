import click
from pathlib import Path
from hrtf.reporting.html_report import ReportGenerator

@click.command()
@click.argument('run_id')
@click.option('--format', type=click.Choice(['json', 'html', 'pdf', 'sarif']), default='html', help='Report format')
@click.option('--output', default='results', help='Output directory')
def report(run_id, format, output):
    """Generate reports."""
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if format == 'html':
        generator = ReportGenerator()
        try:
            path = generator.generate(run_id, output_dir=out_dir)
            click.echo(click.style(f"Generated HTML report at {path.absolute()}", fg="green"))
        except Exception as e:
            click.echo(click.style(f"Error generating report: {e}", fg="red"))
    else:
        click.echo(click.style(f"Format {format} not fully implemented yet.", fg="yellow"))
