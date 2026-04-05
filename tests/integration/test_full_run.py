import pytest
import tempfile
from pathlib import Path
from hrtf.execution.orchestrator import ExecutionOrchestrator
from hrtf.core.types import Verdict

VALID_URDF = b"""
<robot name="test_robot">
    <link name="base_link">
        <inertial>
            <mass value="1.0" />
            <inertia ixx="1.0" ixy="0.0" ixz="0.0" iyy="1.0" iyz="0.0" izz="1.0" />
        </inertial>
    </link>
</robot>
"""

VALID_SCENARIO = """
scenario:
  name: "Basic test"
  robot:
    model: "{urdf_path}"
  simulator:
    backend: "mujoco"
    seed: 42
    step_size: 0.002
  initial_conditions:
    pose:
      position: [0.0, 0.0, 1.0]
  duration: 0.1
  assertions:
    - type: "never_exceeds"
      signal: "/com_height"
      value: 100.0
      window: [0.0, 0.1]
"""

@pytest.fixture
def test_workspace(tmp_path):
    urdf = tmp_path / "robot.urdf"
    urdf.write_bytes(VALID_URDF)

    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(VALID_SCENARIO.format(urdf_path=str(urdf)))

    return scenario

def test_execution_orchestrator(test_workspace):
    orchestrator = ExecutionOrchestrator()
    result = orchestrator.run_scenario(test_workspace)

    assert result.verdict == Verdict.PASS
    assert len(result.assertion_results) == 1
    assert result.assertion_results[0].verdict == Verdict.PASS
    assert result.scenario_name == "Basic test"
