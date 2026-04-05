import click
import subprocess
from pathlib import Path

@click.command()
def ui():
    """Launch the HRTF Streamlit web dashboard."""
    app_path = Path(__file__).parent.parent / "ui" / "app.py"
    if not app_path.exists():
        click.echo(click.style(f"Error: UI app not found at {app_path}", fg="red"))
        return

    click.echo(click.style("Starting HRTF Web Dashboard...", fg="green"))
    subprocess.run(["streamlit", "run", str(app_path)])
