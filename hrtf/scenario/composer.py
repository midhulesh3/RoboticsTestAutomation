"""Composes a ScenarioConfig from separate fixture, test case, and run settings files."""

import yaml
import hashlib
from pathlib import Path

from hrtf.core.types import (
    ScenarioConfig,
    InitialConditions,
    Pose,
    DisturbanceProfile,
    AssertionSpec,
)
from hrtf.core.exceptions import HRTFScenarioError


# Default directory locations (relative to project root)
FIXTURES_DIR = Path("fixtures")
TEST_CASES_DIR = Path("test_cases")
RUN_SETTINGS_DIR = Path("run_settings")


def _load_yaml(path: Path, expected_root: str) -> dict:
    if not path.exists():
        raise HRTFScenarioError(f"File not found: {path}", file_path=path)

    content = path.read_text()
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise HRTFScenarioError(f"Invalid YAML in {path}: {e}", file_path=path)

    if expected_root not in data:
        raise HRTFScenarioError(
            f"Missing '{expected_root}' root key in {path}", file_path=path
        )
    return data[expected_root]


def resolve_fixture(fixture_name: str, fixtures_dir: Path = FIXTURES_DIR) -> Path:
    """Resolve a fixture name to a YAML file path."""
    path = fixtures_dir / f"{fixture_name}.yaml"
    if not path.exists():
        # Try without assuming .yaml was stripped
        path = fixtures_dir / fixture_name
        if not path.exists():
            raise HRTFScenarioError(
                f"Fixture '{fixture_name}' not found in {fixtures_dir}"
            )
    return path


def compose(
    fixture_path: Path,
    test_case_path: Path,
    run_settings_path: Path,
    param_overrides: dict[str, str] | None = None,
) -> ScenarioConfig:
    """Compose a ScenarioConfig from three separate YAML files."""

    fixture = _load_yaml(fixture_path, "fixture")
    test_case = _load_yaml(test_case_path, "test_case")
    run_settings = _load_yaml(run_settings_path, "run_settings")

    # Compute a combined hash for traceability
    combined_content = (
        fixture_path.read_text()
        + test_case_path.read_text()
        + run_settings_path.read_text()
    )
    source_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

    # --- Fixture: robot + initial conditions ---
    robot_data = fixture.get("robot", {})
    ic_data = fixture.get("initial_conditions", {})
    pose_data = ic_data.get("pose", {})

    # Resolve robot model path relative to project root
    robot_model = robot_data.get("model", "")

    pose = Pose(
        position=tuple(pose_data.get("position", [0.0, 0.0, 0.0])),
        orientation=tuple(pose_data.get("orientation", [0.0, 0.0, 0.0, 1.0])),
    )

    initial_conditions = InitialConditions(
        pose=pose,
        joint_positions=ic_data.get("joint_positions", {}),
    )

    # --- Test case: disturbances, assertions, duration ---
    disturbances = []
    for dist_data in test_case.get("disturbance", []):
        disturbances.append(
            DisturbanceProfile(
                type=dist_data.get("type"),
                time=dist_data.get("time"),
                force=tuple(dist_data.get("force")) if dist_data.get("force") else None,
                duration=dist_data.get("duration"),
                mass=dist_data.get("mass"),
                link=dist_data.get("link", "base_link"),
            )
        )

    assertions = []
    for assert_data in test_case.get("assertions", []):
        assertions.append(
            AssertionSpec(
                type=assert_data.get("type"),
                signal=assert_data.get("signal"),
                value=assert_data.get("value"),
                window=tuple(assert_data.get("window")) if assert_data.get("window") else None,
                tolerance=assert_data.get("tolerance"),
                operator=assert_data.get("operator"),
            )
        )

    # --- Run settings: simulator config ---
    sim_data = run_settings.get("simulator", {})

    # Apply CLI overrides if provided
    if param_overrides:
        for key, value in param_overrides.items():
            parts = key.split(".")
            if parts[0] == "simulator" and len(parts) == 2:
                orig = sim_data.get(parts[1])
                if isinstance(orig, int):
                    value = int(value)
                elif isinstance(orig, float):
                    value = float(value)
                sim_data[parts[1]] = value
            elif key == "duration":
                # Allow overriding duration
                pass  # handled below

    duration = test_case.get("duration", 0.0)
    if param_overrides and "duration" in param_overrides:
        duration = float(param_overrides["duration"])

    return ScenarioConfig(
        name=test_case.get("name", "Unnamed Test Case"),
        description=test_case.get("description", ""),
        robot_source=robot_model,
        simulator_backend=sim_data.get("backend", "mujoco"),
        seed=sim_data.get("seed", 42),
        step_size=sim_data.get("step_size", 0.001),
        real_time_factor=sim_data.get("real_time_factor", 0.0),
        initial_conditions=initial_conditions,
        disturbances=disturbances,
        duration=duration,
        assertions=assertions,
        metadata=test_case.get("metadata", {}),
        source_path=f"{fixture_path}+{test_case_path}+{run_settings_path}",
        source_hash=source_hash,
    )
