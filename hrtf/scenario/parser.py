import yaml
import hashlib
from pathlib import Path
from hrtf.core.types import (
    ScenarioConfig,
    InitialConditions,
    Pose,
    DisturbanceProfile,
    AssertionSpec
)
from hrtf.core.exceptions import HRTFScenarioError

class ScenarioParser:
    def __init__(self):
        # We'll skip strict jsonschema validation for now and rely on manual basic checking
        pass

    def parse(self, path: str | Path, param_overrides: dict[str, str] | None = None) -> ScenarioConfig:
        path = Path(path)
        if not path.exists():
            raise HRTFScenarioError(f"Scenario file not found: {path}", file_path=path)

        content = path.read_text()
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise HRTFScenarioError(f"Invalid YAML in {path}: {e}", file_path=path)

        if "scenario" not in data:
            raise HRTFScenarioError("Missing 'scenario' root key", file_path=path)

        scenario_data = data["scenario"]

        # Hash the source content
        source_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        # Basic defaults and minimal parsing for the PoC
        robot_data = scenario_data.get("robot", {})
        simulator_data = scenario_data.get("simulator", {})
        ic_data = scenario_data.get("initial_conditions", {})
        pose_data = ic_data.get("pose", {})

        pose = Pose(
            position=tuple(pose_data.get("position", [0.0, 0.0, 0.0])),
            orientation=tuple(pose_data.get("orientation", [0.0, 0.0, 0.0, 1.0]))
        )

        initial_conditions = InitialConditions(
            pose=pose,
            joint_positions=ic_data.get("joint_positions", {})
        )

        disturbances = []
        for dist_data in scenario_data.get("disturbance", []):
            disturbances.append(DisturbanceProfile(
                type=dist_data.get("type"),
                time=dist_data.get("time"),
                force=tuple(dist_data.get("force")) if dist_data.get("force") else None,
                duration=dist_data.get("duration"),
                mass=dist_data.get("mass"),
                link=dist_data.get("link", "base_link")
            ))

        assertions = []
        for assert_data in scenario_data.get("assertions", []):
            assertions.append(AssertionSpec(
                type=assert_data.get("type"),
                signal=assert_data.get("signal"),
                value=assert_data.get("value"),
                window=tuple(assert_data.get("window")) if assert_data.get("window") else None,
                tolerance=assert_data.get("tolerance"),
                operator=assert_data.get("operator")
            ))

        return ScenarioConfig(
            name=scenario_data.get("name", "Unnamed Scenario"),
            description=scenario_data.get("description", ""),
            robot_source=robot_data.get("model", ""),
            simulator_backend=simulator_data.get("backend", "gazebo"),
            seed=simulator_data.get("seed", 42),
            step_size=simulator_data.get("step_size", 0.001),
            real_time_factor=simulator_data.get("real_time_factor", 0.0),
            initial_conditions=initial_conditions,
            disturbances=disturbances,
            duration=scenario_data.get("duration", 0.0),
            assertions=assertions,
            metadata=scenario_data.get("metadata", {}),
            source_path=str(path),
            source_hash=source_hash
        )