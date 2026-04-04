import pytest
import tempfile
from pathlib import Path
from hrtf.scenario.parser import ScenarioParser

def test_scenario_parser():
    yaml_content = """
hrtf_version: "1.0"
scenario:
  name: "Lateral Push Recovery"
  description: "Validates CoM recovery after 50N lateral impulse"
  robot:
    model: "unitree_g1"
  simulator:
    backend: "gazebo"
    seed: 42
    step_size: 0.001
    real_time_factor: 0.0
  initial_conditions:
    pose:
      position: [0.0, 0.0, 1.0]
      orientation: [0.0, 0.0, 0.0, 1.0]
    joint_positions:
      left_hip_pitch: -0.3
      left_knee: 0.6
  disturbance:
    - type: "impulse"
      time: 5.0
      force: [50.0, 0.0, 0.0]
      duration: 0.2
      link: "base_link"
  duration: 15.0
  assertions:
    - type: "always_above"
      signal: "/com_height"
      value: 0.75
      window: [5.0, 15.0]
  metadata:
    author: "test-team"
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        parser = ScenarioParser()
        config = parser.parse(temp_path)

        assert config.name == "Lateral Push Recovery"
        assert config.robot_source == "unitree_g1"
        assert config.simulator_backend == "gazebo"
        assert config.seed == 42
        assert config.initial_conditions.pose.position == (0.0, 0.0, 1.0)
        assert config.initial_conditions.joint_positions["left_knee"] == 0.6
        assert len(config.disturbances) == 1
        assert config.disturbances[0].type == "impulse"
        assert config.disturbances[0].force == (50.0, 0.0, 0.0)
        assert len(config.assertions) == 1
        assert config.assertions[0].type == "always_above"
        assert config.assertions[0].signal == "/com_height"
        assert config.duration == 15.0
        assert config.metadata["author"] == "test-team"
    finally:
        Path(temp_path).unlink()
