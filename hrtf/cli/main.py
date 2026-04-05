import click
from .run import run
from .init import init
from .baseline import baseline
from .report import report
from .ui import ui

@click.group()
def cli():
    """Humanoid Robot Test Framework."""
    pass

cli.add_command(run)
cli.add_command(init)
cli.add_command(baseline)
cli.add_command(report)
cli.add_command(ui)

if __name__ == '__main__':
    cli()