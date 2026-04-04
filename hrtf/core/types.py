from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"

@dataclass
class Pose:
    position: tuple[float, float, float]
    orientation: tuple[float, float, float, float]

@dataclass
class JointLimits:
    lower: float
    upper: float
    effort_limit: float
    velocity_limit: float

@dataclass
class DisturbanceProfile:
    type: Literal["impulse", "static_load", "sinusoidal"]
    time: float
    force: tuple[float, float, float] | None = None
    duration: float | None = None
    mass: float | None = None
    link: str = "base_link"

@dataclass
class InitialConditions:
    pose: Pose
    joint_positions: dict[str, float] = field(default_factory=dict)

@dataclass
class SignalSummary:
    mean: float
    min: float
    max: float
    std: float
    final_value: float
    sample_count: int

@dataclass
class AssertionResult:
    verdict: Verdict
    assertion_type: str
    signal_name: str
    first_violation_time: float | None = None
    violation_value: float | None = None
    expected_bound: float | None = None
    violation_duration: float | None = None
    signal_summary: SignalSummary | None = None

@dataclass
class ScenarioResult:
    scenario_name: str
    scenario_source: str
    scenario_hash: str
    verdict: Verdict
    sim_duration: float
    wall_clock_duration: float
    assertion_results: list[AssertionResult]
    signal_summaries: dict[str, SignalSummary]
    error_message: str | None = None
    stack_trace: str | None = None

@dataclass
class EvidenceManifest:
    scenario_yaml_hash: str
    robot_urdf_hash: str
    simulator: str
    simulator_version: str
    seed: int
    hrtf_version: str
    python_version: str
    os_info: str

@dataclass
class RunResult:
    run_id: str
    timestamp: datetime
    overall_verdict: Verdict
    scenarios: list[ScenarioResult]
    evidence_manifest: EvidenceManifest
    total_wall_clock: float

@dataclass
class AssertionSpec:
    type: str
    signal: str | None = None
    value: float | None = None
    window: tuple[float, float] | None = None
    tolerance: float | None = None
    operator: str | None = None
    children: list["AssertionSpec"] | None = None

@dataclass
class ScenarioConfig:
    name: str
    description: str
    robot_source: str
    simulator_backend: str
    seed: int
    step_size: float
    real_time_factor: float
    initial_conditions: InitialConditions
    disturbances: list[DisturbanceProfile]
    duration: float
    assertions: list[AssertionSpec]
    metadata: dict[str, str]
    source_path: str
    source_hash: str
