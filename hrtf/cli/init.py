import click
from pathlib import Path

SCENARIO_TEMPLATE = """hrtf_version: "1.0"

scenario:
  name: "{scenario_name}"
  description: "Generated scenario template"

  robot:
    model: "{robot_urdf}"

  simulator:
    backend: "mujoco"
    seed: 42
    step_size: 0.002
    real_time_factor: 0.0

  initial_conditions:
    pose:
      position: [0.0, 0.0, 1.0]
      orientation: [0.0, 0.0, 0.0, 1.0]

  duration: 10.0

  assertions:
    - type: "always_above"
      signal: "/com_height"
      value: 0.75
      window: [0.0, 10.0]
"""

@click.command()
@click.argument('robot_urdf')
@click.option('--scenario-type', default='balance', help='Scenario type (e.g., balance, gait)')
@click.option('--output', default='scenario.yaml', help='Output path for the generated template')
def init(robot_urdf, scenario_type, output):
    """Generate scenario template."""
    click.echo(f"Initializing '{scenario_type}' scenario template for {robot_urdf}...")

    out_path = Path(output)

    scenario_name = f"{scenario_type.capitalize()} Test"
    content = SCENARIO_TEMPLATE.format(
        scenario_name=scenario_name,
        robot_urdf=robot_urdf
    )

    out_path.write_text(content)
    click.echo(click.style(f"Created template at {out_path.absolute()}", fg="green"))
