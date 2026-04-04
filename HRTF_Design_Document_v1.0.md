# HRTF — Humanoid Robot Test Framework: Detailed Design Document

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Date** | April 2026 |
| **Status** | Draft |
| **Based on** | HRTF Requirements Specification v1.0 |
| **Target platform** | Ubuntu 22.04/24.04 LTS, Python 3.10+, ROS 2 Humble/Jazzy |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Package and Module Structure](#3-package-and-module-structure)
4. [Detailed Component Design](#4-detailed-component-design)
   - 4.1 [CLI Layer](#41-cli-layer)
   - 4.2 [Robot Model Loader](#42-robot-model-loader)
   - 4.3 [Scenario Engine](#43-scenario-engine)
   - 4.4 [Simulation Adapter Layer](#44-simulation-adapter-layer)
   - 4.5 [Signal Logger](#45-signal-logger)
   - 4.6 [Assertion Engine](#46-assertion-engine)
   - 4.7 [Baseline Manager](#47-baseline-manager)
   - 4.8 [Report Generator](#48-report-generator)
   - 4.9 [CI/CD Integration](#49-cicd-integration)
5. [Data Models and Schemas](#5-data-models-and-schemas)
6. [Built-in Scenario Library Design](#6-built-in-scenario-library-design)
7. [Simulation Determinism Strategy](#7-simulation-determinism-strategy)
8. [Error Handling Strategy](#8-error-handling-strategy)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Phased Implementation Plan](#11-phased-implementation-plan)
12. [Design Decisions and Trade-offs](#12-design-decisions-and-trade-offs)
13. [Appendix: Requirement Traceability](#13-appendix-requirement-traceability)

---

## 1. Introduction

### 1.1 Purpose of This Document

This design document translates the HRTF Requirements Specification v1.0 into a concrete software architecture, module decomposition, interface definitions, data models, and implementation strategy. It is the primary technical reference for developers building HRTF.

### 1.2 Design Goals

| Goal | Rationale |
|---|---|
| **Pluggable simulation back-ends** | Different teams use Gazebo, MuJoCo, or Isaac Sim. The adapter pattern isolates simulator-specific code. |
| **Zero-code test authoring** | YAML-first scenarios lower the barrier to entry for robotics engineers who are not Python developers. |
| **Deterministic by default** | Reproducibility is non-negotiable for regression testing. Seeded determinism must be a first-class concern in every adapter. |
| **CI-native** | HRTF must be a CLI tool first. All features must be usable headlessly; GUIs are optional layers on top. |
| **Extensible without forking** | Plugin interfaces (adapters, assertions, scenario types) via Python entry points. |

### 1.3 Constraints Recap

- **OS**: Ubuntu 22.04 / 24.04 LTS only at MVP
- **Python**: 3.10+
- **ROS 2**: Humble Hawksbill (LTS), optional Jazzy Jalisco
- **Dependencies**: pip + apt installable, no proprietary licenses for core
- **MATLAB/Simulink**: Optional; degrade gracefully when absent

---

## 2. System Architecture

### 2.1 Layered Architecture Overview

```
+================================================================+
|                     CLI / Python API Layer                      |
|  hrtf run | hrtf init | hrtf baseline | hrtf report            |
+================================================================+
         |                    |                    |
         v                    v                    v
+------------------+  +------------------+  +------------------+
|  Scenario Engine |  | Baseline Manager |  | Report Generator |
|  (YAML parse,    |  | (capture, store, |  | (JSON, HTML, PDF)|
|   validate,      |  |  compare, diff)  |  |                  |
|   parameterise)  |  +------------------+  +------------------+
+------------------+           |
         |                     |
         v                     v
+================================================================+
|                    Execution Orchestrator                       |
|  (sequential / parallel dispatch, timeout, crash recovery)     |
+================================================================+
         |
         v
+================================================================+
|                  Simulation Adapter Layer                       |
|  SimulatorAdapter ABC                                          |
|  +------------------+ +------------------+ +------------------+|
|  | GazeboAdapter    | | MuJoCoAdapter    | | IsaacSimAdapter  ||
|  | (ROS 2 bridge)   | | (Python bindings)| | (Python API)     ||
|  +------------------+ +------------------+ +------------------+|
+================================================================+
         |
         v
+================================================================+
|                      Signal Logger                             |
|  (ROS 2 topic subscription, buffered telemetry capture)        |
+================================================================+
         |
         v
+================================================================+
|                     Assertion Engine                            |
|  always_above | never_exceeds | reaches_within |               |
|  stabilises_within | event_occurs | compound(AND/OR)           |
+================================================================+
         |
         v
+================================================================+
|                       Result Store                             |
|  (JSON result files, baseline files, signal data)              |
+================================================================+
```

### 2.2 Key Data Flows

**Flow 1: Test Execution (`hrtf run`)**

```
Scenario YAML --> Scenario Engine (parse + validate)
                       |
                       v
              Robot Model Loader (URDF/SDF parse + validate)
                       |
                       v
              Execution Orchestrator (select adapter, configure seed)
                       |
                       v
              SimulatorAdapter.setup() --> spawn simulator process
              SimulatorAdapter.load_robot(urdf_path)
              SimulatorAdapter.apply_disturbance(profile)
              Signal Logger.start() --> subscribe to ROS 2 topics
                       |
                       v (simulation runs for scenario.duration)
              Signal Logger.stop() --> flush buffers
              SimulatorAdapter.teardown() --> kill simulator
                       |
                       v
              Assertion Engine.evaluate(signal_log, assertions)
                       |
                       v
              Result Store.write(result_json)
              Report Generator.generate(result_json, format=[json, html])
```

**Flow 2: Baseline Workflow (`hrtf baseline capture` / `hrtf baseline compare`)**

```
Capture:
  result_json --> Baseline Manager.capture(run_id, name)
                       |
                       v
              Extract summary stats per signal --> write baseline JSON

Compare:
  new result_json + baseline JSON --> Baseline Manager.compare()
                       |
                       v
              Per-signal delta computation (abs + %)
                       |
                       v
              Apply tolerance threshold (default 5%)
                       |
                       v
              Verdict: PASS | REGRESSED (with per-metric detail)
```

### 2.3 Process Architecture

```
+----------------------------------------------------+
|  hrtf CLI process (Python)                         |
|                                                     |
|  Scenario Engine, Assertion Engine, Report Gen      |
|                                                     |
|  +----------------------------------------------+  |
|  | Execution Orchestrator                        |  |
|  |                                                |  |
|  |  Worker 1          Worker 2       Worker N    |  |
|  |  (subprocess)      (subprocess)   (subprocess)|  |
|  |  [GazeboAdapter]   [MuJoCoAdapter] ...        |  |
|  +----------------------------------------------+  |
+----------------------------------------------------+
         |                    |                |
         v                    v                v
   [gzserver]          [mujoco_sim]      [isaac_sim]
   (external process)  (in-process)      (external)
```

- Each scenario runs in its own worker subprocess for isolation (requirement RB-02)
- Workers communicate results back to the orchestrator via serialized JSON over pipes
- Configurable worker count (default: `min(cpu_count, scenario_count)`)

---

## 3. Package and Module Structure

```
hrtf/
  __init__.py                  # version, public API exports
  __main__.py                  # entry point: python -m hrtf
  
  cli/
    __init__.py
    main.py                    # Click-based CLI root group
    run.py                     # hrtf run command
    init.py                    # hrtf init command
    baseline.py                # hrtf baseline capture/compare commands
    report.py                  # hrtf report command
  
  core/
    __init__.py
    config.py                  # Global configuration and defaults
    types.py                   # Shared data classes (ScenarioConfig, RunResult, etc.)
    exceptions.py              # HRTF-specific exception hierarchy
  
  models/
    __init__.py
    loader.py                  # URDF/SDF loading and validation
    validator.py               # Structural URDF/SDF validation with diagnostics
    reference/                 # Bundled reference URDFs
      unitree_g1/
      unitree_h1/
      icub/
  
  scenario/
    __init__.py
    parser.py                  # YAML scenario parsing
    validator.py               # JSON Schema validation of scenario YAML
    parameterizer.py           # CLI override application
    inheritance.py             # Scenario extends/override resolution
    schema/
      scenario_v1.json         # Published JSON Schema for scenario YAML
    library/                   # Built-in canonical scenarios (SC-01..SC-10)
      static_balance.yaml
      lateral_push_recovery.yaml
      flat_ground_gait.yaml
      joint_torque_compliance.yaml
      stair_ascent.yaml
      fall_detection_estop.yaml
      payload_walking.yaml
      slope_ascent.yaml
      object_grasp.yaml
      push_recovery_manipulation.yaml
  
  adapters/
    __init__.py
    base.py                    # SimulatorAdapter ABC
    gazebo/
      __init__.py
      adapter.py               # GazeboHarmonicAdapter
      bridge.py                # ROS 2 bridge helpers
      launch.py                # Gazebo process management
    mujoco/
      __init__.py
      adapter.py               # MuJoCoAdapter
      renderer.py              # Optional MuJoCo viewer integration
    isaac_sim/                 # v1.0 phase
      __init__.py
      adapter.py               # IsaacSimAdapter
  
  signals/
    __init__.py
    logger.py                  # ROS 2 topic subscriber + buffered writer
    store.py                   # Signal data persistence (HDF5/Parquet)
    reader.py                  # Signal data read API
  
  assertions/
    __init__.py
    engine.py                  # Assertion evaluation orchestrator
    predicates.py              # Built-in predicates (always_above, etc.)
    compound.py                # AND/OR compound assertion logic
    registry.py                # Plugin registry for custom assertions
    types.py                   # AssertionResult, Violation data classes
  
  baselines/
    __init__.py
    manager.py                 # Capture, store, compare logic
    diff.py                    # Per-signal delta computation
    store.py                   # Baseline file I/O (JSON, git-friendly)
  
  reporting/
    __init__.py
    json_report.py             # Machine-readable JSON result output
    html_report.py             # HTML report with embedded signal plots
    pdf_report.py              # PDF executive summary (WeasyPrint)
    plots.py                   # Matplotlib signal plot generation
    sarif.py                   # SARIF format output (v1.0)
    templates/
      report.html.jinja2       # Jinja2 HTML report template
      summary.html.jinja2      # Executive summary template
  
  execution/
    __init__.py
    orchestrator.py            # Sequential/parallel scenario dispatch
    worker.py                  # Subprocess worker for scenario execution
    timeout.py                 # Scenario timeout management
    recovery.py                # Simulator crash detection and recovery
  
  export/
    __init__.py
    mat_export.py              # .mat file export for Simulink (v1.0)

tests/
  unit/
    test_loader.py
    test_scenario_parser.py
    test_assertions.py
    test_baseline_manager.py
    test_report_generator.py
    ...
  integration/
    test_gazebo_adapter.py
    test_mujoco_adapter.py
    test_full_run.py
    ...
  scenarios/                   # Test scenario fixtures
    valid_scenario.yaml
    invalid_scenario.yaml
    ...

docker/
  Dockerfile                   # Official Docker image
  docker-compose.yml           # Dev environment with Gazebo
  entrypoint.sh

ci/
  hrtf.yml                     # GitHub Actions workflow template
  .gitlab-ci.yml               # GitLab CI snippet

docs/
  quickstart.md
  scenario_authoring.md
  adapter_guide.md
  api_reference.md

pyproject.toml                 # Package metadata, dependencies, entry points
CLAUDE.md                      # Dev conventions for this repo
```

---

## 4. Detailed Component Design

### 4.1 CLI Layer

**Technology**: [Click](https://click.palletsprojects.com/) (chosen over argparse for subcommand composition and automatic `--help` generation)

**Commands**:

| Command | Description | Key Flags | Req IDs |
|---|---|---|---|
| `hrtf run <scenario.yaml>` | Execute one or more scenarios | `--sim {gazebo,mujoco,isaac}`, `--seed INT`, `--workers INT`, `--output-dir PATH`, `--param key=value` | CI-01, SA-04 |
| `hrtf run --suite <suite.yaml>` | Execute a named test suite | Same as above | SA-07 |
| `hrtf init <robot.urdf>` | Generate scenario template | `--scenario-type {balance,gait,...}`, `--output PATH` | SA-02 |
| `hrtf baseline capture <run_id> <name>` | Capture baseline from run | `--store PATH` | BL-01 |
| `hrtf baseline compare <run_id> <baseline>` | Compare run to baseline | `--tolerance FLOAT`, `--format {json,table}` | BL-02 |
| `hrtf baseline list` | List stored baselines | `--store PATH` | BL-01 |
| `hrtf report <run_id>` | Generate reports | `--format {json,html,pdf,sarif}`, `--output PATH` | RP-01..04 |
| `hrtf validate <scenario.yaml>` | Validate scenario without running | | SA-03 |

**Exit Codes** (RP-03):

| Code | Meaning |
|---|---|
| 0 | All scenarios passed |
| 1 | One or more scenarios failed assertions |
| 2 | One or more scenarios errored (simulator crash, timeout) |
| 3 | Invalid input (bad YAML, missing URDF) |

**Python API** (programmatic use):

```python
from hrtf import run_scenario, capture_baseline, compare_baseline

result = run_scenario(
    scenario_path="scenarios/static_balance.yaml",
    simulator="gazebo",
    seed=42,
    param_overrides={"duration": 60.0}
)

assert result.verdict == "PASS"
```

### 4.2 Robot Model Loader

**Responsibilities**: Load, parse, validate URDF/SDF files and surface actionable errors (RL-01..RL-06).

```python
# hrtf/models/loader.py

@dataclass
class RobotModel:
    """Parsed and validated robot model."""
    name: str
    urdf_path: Path
    urdf_hash: str               # SHA-256 of URDF file (RL-06)
    format: Literal["urdf", "sdf"]
    joints: list[JointInfo]      # name, type, limits
    links: list[LinkInfo]        # name, mass, inertia
    joint_limits: dict[str, JointLimits]
    
    def with_overrides(self, overrides: dict) -> "RobotModel":
        """Return a copy with joint limit overrides applied (RL-05)."""
        ...

class RobotModelLoader:
    """Load and validate robot models from URDF/SDF."""
    
    REFERENCE_MODELS = {
        "unitree_g1": "hrtf/models/reference/unitree_g1/g1.urdf",
        "unitree_h1": "hrtf/models/reference/unitree_h1/h1.urdf",
        "icub": "hrtf/models/reference/icub/icub.urdf",
    }
    
    def load(self, source: str | Path) -> RobotModel:
        """
        Load from:
        - File path: /path/to/robot.urdf
        - Reference name: "unitree_g1"
        - ROS 2 parameter: "ros2://robot_description"
        
        Raises HRTFModelError with structured diagnostics on failure.
        """
        ...
    
    def _validate_urdf(self, urdf_path: Path) -> list[ValidationDiagnostic]:
        """
        Structural validation (RL-03):
        - Well-formed XML
        - Required elements present (robot, link, joint)
        - Joint types valid
        - Mass/inertia values non-negative
        - Joint limits consistent (lower < upper)
        - Kinematic tree is connected
        
        Returns list of diagnostics with:
        - severity: error | warning
        - element: XML element name
        - line_number: line in the URDF file
        - message: human-readable description
        - suggestion: actionable fix
        """
        ...
```

**Validation diagnostic output example (UX-03)**:

```
ERROR in robot.urdf:47 — Joint 'left_knee' has lower_limit (1.5) > upper_limit (0.0)
  Fix: Swap the lower and upper limit values, or set lower_limit to a negative value.

WARNING in robot.urdf:83 — Link 'right_foot' has zero mass. 
  This may cause simulation instability. Set a small positive mass (e.g., 0.01 kg).
```

### 4.3 Scenario Engine

**Responsibilities**: Parse, validate, parameterize, and resolve YAML scenario definitions.

#### 4.3.1 Scenario YAML Schema (SA-01)

```yaml
# scenario_v1 schema
hrtf_version: "1.0"                    # Schema version

scenario:
  name: "Lateral Push Recovery"
  description: "Validates CoM recovery after 50N lateral impulse"
  
  robot:
    model: "unitree_g1"                # Reference name or path
    # model: "/path/to/custom.urdf"    # Alternative: file path
    joint_overrides:                    # Optional (RL-05)
      left_knee:
        effort_limit: 80.0
  
  simulator:
    backend: "gazebo"                  # gazebo | mujoco | isaac_sim
    seed: 42                           # Random seed for determinism
    step_size: 0.001                   # Simulation step size in seconds
    real_time_factor: 0.0              # 0 = as fast as possible
  
  initial_conditions:
    pose:
      position: [0.0, 0.0, 1.0]       # x, y, z in meters
      orientation: [0.0, 0.0, 0.0, 1.0]  # quaternion (x, y, z, w)
    joint_positions:                   # Optional: initial joint angles
      left_hip_pitch: -0.3
      left_knee: 0.6
  
  disturbance:
    - type: "impulse"
      time: 5.0                        # Apply at t=5s
      force: [50.0, 0.0, 0.0]         # Newtons (x, y, z) in world frame
      duration: 0.2                    # Duration of impulse in seconds
      link: "base_link"               # Target link
  
  duration: 15.0                       # Total scenario duration in seconds
  
  assertions:
    - type: "always_above"
      signal: "/com_height"
      value: 0.75
      window: [5.0, 15.0]             # From disturbance to end
    
    - type: "stabilises_within"
      signal: "/com_height"
      tolerance: 0.02
      window: [5.0, 12.0]             # Must stabilise within 7s of push
    
    - type: "never_exceeds"
      signal: "/joint_torques/left_ankle"
      value: 100.0
      window: [0.0, 15.0]
  
  metadata:                            # Optional key-value pairs
    author: "test-team"
    ticket: "HRTF-42"
```

#### 4.3.2 Scenario Inheritance (SA-06)

```yaml
hrtf_version: "1.0"

extends: "flat_ground_gait.yaml"       # Base scenario

scenario:
  name: "Payload Walking — 5 kg"
  
  # Only override what changes
  disturbance:
    - type: "static_load"
      mass: 5.0
      link: "torso"
      offset: [0.0, 0.0, 0.3]
  
  assertions:
    - $inherit                         # Keep all base assertions
    - type: "never_exceeds"            # Add one more
      signal: "/joint_torques/*"
      value_expr: "joint.rated_torque * 0.90"
      window: [0.0, 12.0]
```

**Resolution algorithm**:
1. Load base scenario recursively (max depth = 5 to prevent cycles)
2. Deep-merge fields: child values override parent; `$inherit` in lists means append
3. Validate merged result against JSON Schema

#### 4.3.3 Parameterization (SA-04)

CLI overrides apply after inheritance resolution:

```bash
hrtf run push_recovery.yaml --param disturbance.0.force.0=80 --param duration=20
```

Implementation: dot-path keys are resolved into the scenario dict via recursive descent. Type coercion uses the JSON Schema type declarations.

#### 4.3.4 Scenario Parser Class

```python
# hrtf/scenario/parser.py

@dataclass
class ScenarioConfig:
    """Fully resolved, validated scenario configuration."""
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
    source_path: Path
    source_hash: str  # SHA-256 for reproducibility (RP-05)

class ScenarioParser:
    def __init__(self, schema_path: Path = DEFAULT_SCHEMA_PATH):
        self._schema = json.loads(schema_path.read_text())
        self._validator = jsonschema.Draft7Validator(self._schema)
    
    def parse(
        self,
        path: Path,
        param_overrides: dict[str, str] | None = None
    ) -> ScenarioConfig:
        """
        1. Load YAML
        2. Resolve inheritance chain
        3. Apply CLI param overrides
        4. Validate against JSON Schema (SA-03)
        5. Return typed ScenarioConfig
        
        Raises HRTFScenarioError with line-level diagnostics on failure.
        """
        ...
```

### 4.4 Simulation Adapter Layer

**Design Pattern**: Abstract Base Class (ABC) with concrete implementations per simulator.

#### 4.4.1 SimulatorAdapter ABC (SE-05)

```python
# hrtf/adapters/base.py

from abc import ABC, abstractmethod

class SimulatorAdapter(ABC):
    """
    Abstract interface for simulation back-ends.
    
    Third-party adapters must implement all abstract methods.
    Target: < 200 lines of Python for a minimal adapter (SE-05).
    
    Lifecycle:
        adapter = MyAdapter(config)
        adapter.setup()          # Spawn simulator, configure physics
        adapter.load_robot(...)  # Insert robot model
        adapter.configure(...)   # Set seed, step size, etc.
        adapter.run(...)         # Execute simulation loop
        adapter.teardown()       # Clean up processes
    """
    
    @abstractmethod
    def setup(self) -> None:
        """Initialize simulator process/connection."""
        ...
    
    @abstractmethod
    def teardown(self) -> None:
        """Terminate simulator process, release resources."""
        ...
    
    @abstractmethod
    def load_robot(self, model: RobotModel, pose: Pose) -> None:
        """Load robot model into the simulation world at the given pose."""
        ...
    
    @abstractmethod
    def configure(
        self,
        seed: int,
        step_size: float,
        real_time_factor: float
    ) -> None:
        """Configure simulation parameters for deterministic execution."""
        ...
    
    @abstractmethod
    def apply_disturbance(self, disturbance: DisturbanceProfile) -> None:
        """Schedule a disturbance to be applied at the specified time."""
        ...
    
    @abstractmethod
    def run(self, duration: float) -> None:
        """Run simulation for the specified duration."""
        ...
    
    @abstractmethod
    def get_signal_sources(self) -> list[SignalSource]:
        """Return available telemetry signal sources (topics, channels)."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name (e.g., 'Gazebo Harmonic')."""
        ...
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Simulator version string for reproducibility metadata."""
        ...
```

#### 4.4.2 Gazebo Harmonic Adapter (SE-01)

```python
# hrtf/adapters/gazebo/adapter.py

class GazeboHarmonicAdapter(SimulatorAdapter):
    """
    Adapter for Gazebo Harmonic via ROS 2 bridge.
    
    Process model:
    - Spawns gzserver as a subprocess (headless)
    - Uses ros_gz_bridge for topic bridging
    - Applies disturbances via Gazebo transport API (gz.msgs.Wrench)
    
    Determinism (SE-03):
    - Sets GZ_SIM_SEED environment variable
    - Pauses simulation on startup, steps manually via /world/step service
    - No wall-clock coupling (real_time_factor = 0)
    """
    
    def setup(self) -> None:
        # 1. Launch gzserver with empty world
        self._gz_process = subprocess.Popen(
            ["gz", "sim", "-s", "--headless-rendering", "-r", self._world_sdf],
            env={**os.environ, "GZ_SIM_SEED": str(self._seed)}
        )
        # 2. Wait for /world service to become available
        # 3. Launch ros_gz_bridge with configured topic mappings
        # 4. Pause simulation
        ...
    
    def load_robot(self, model: RobotModel, pose: Pose) -> None:
        # Spawn entity via /world/<name>/create service
        ...
    
    def run(self, duration: float) -> None:
        # Step simulation in a loop:
        #   steps = int(duration / self._step_size)
        #   for each step: call /world/<name>/step service
        # This ensures deterministic execution independent of wall clock
        ...
    
    def apply_disturbance(self, disturbance: DisturbanceProfile) -> None:
        # Schedule a wrench application at the target sim time
        # Applied during the run() loop when sim_time >= disturbance.time
        ...
    
    def teardown(self) -> None:
        # SIGTERM gzserver, wait, SIGKILL if needed
        # Kill ros_gz_bridge
        ...
```

#### 4.4.3 MuJoCo Adapter (SE-02)

```python
# hrtf/adapters/mujoco/adapter.py

class MuJoCoAdapter(SimulatorAdapter):
    """
    Adapter for MuJoCo via the mujoco Python bindings.
    
    Process model:
    - Runs in-process (no external simulator to spawn)
    - URDF converted to MJCF on load via mujoco.MjModel.from_xml_path
    
    Determinism (SE-03):
    - MuJoCo is deterministic by default (same model + same initial state
      + same inputs = same outputs). No special seed handling required.
    - Disturbances applied via xfrc_applied array at exact time steps.
    
    Signal publishing:
    - MuJoCo has no native ROS 2 integration
    - This adapter publishes telemetry to ROS 2 topics in the step loop:
        /joint_states       -> sensor_msgs/JointState
        /com_position       -> geometry_msgs/Point
        /base_pose          -> geometry_msgs/PoseStamped
    """
    
    def setup(self) -> None:
        # No external process needed
        self._model: mujoco.MjModel = None
        self._data: mujoco.MjData = None
        ...
    
    def load_robot(self, model: RobotModel, pose: Pose) -> None:
        # Convert URDF to MJCF if needed
        # Load into MuJoCo
        self._model = mujoco.MjModel.from_xml_path(str(mjcf_path))
        self._data = mujoco.MjData(self._model)
        # Set initial pose
        ...
    
    def run(self, duration: float) -> None:
        steps = int(duration / self._model.opt.timestep)
        for step in range(steps):
            # Apply scheduled disturbances
            current_time = step * self._model.opt.timestep
            self._apply_scheduled_forces(current_time)
            
            # Step physics
            mujoco.mj_step(self._model, self._data)
            
            # Publish telemetry to ROS 2 topics
            self._publish_telemetry(current_time)
        ...
```

#### 4.4.4 Adapter Registry

```python
# hrtf/adapters/__init__.py

BUILTIN_ADAPTERS: dict[str, type[SimulatorAdapter]] = {
    "gazebo": GazeboHarmonicAdapter,
    "mujoco": MuJoCoAdapter,
}

# Third-party adapters register via entry points:
# [project.entry-points."hrtf.adapters"]
# isaac_sim = "hrtf_isaac:IsaacSimAdapter"

def get_adapter(name: str, config: SimulatorConfig) -> SimulatorAdapter:
    """Resolve adapter by name, checking built-in registry then entry points."""
    if name in BUILTIN_ADAPTERS:
        return BUILTIN_ADAPTERS[name](config)
    
    # Check entry points
    for ep in importlib.metadata.entry_points(group="hrtf.adapters"):
        if ep.name == name:
            adapter_cls = ep.load()
            return adapter_cls(config)
    
    raise HRTFAdapterError(
        f"Unknown simulator '{name}'. "
        f"Available: {list(BUILTIN_ADAPTERS.keys())}. "
        f"Install a plugin or check 'hrtf.adapters' entry points."
    )
```

### 4.5 Signal Logger

**Responsibilities**: Subscribe to ROS 2 topics, buffer telemetry at native frequency, persist to disk (AS-01, PF-03).

```python
# hrtf/signals/logger.py

class SignalLogger:
    """
    High-performance ROS 2 telemetry logger.
    
    Design:
    - Subscribes to all topics matching configurable patterns
    - Double-buffered: front buffer receives messages, back buffer
      flushes to disk on a background thread
    - Zero-copy where possible via ROS 2 message introspection
    - Persists to Apache Parquet (columnar, compressed, fast random access)
      with fallback to HDF5 for MATLAB compatibility
    
    Performance target (PF-03):
    - Zero sample loss at up to 1 kHz per topic
    - Achieved via pre-allocated numpy arrays sized to
      (duration * frequency * 1.1) with overflow ring buffer
    """
    
    def __init__(
        self,
        node: rclpy.node.Node,
        topic_patterns: list[str] = ["/**"],  # Subscribe to all by default
        buffer_size: int = 100_000,
        output_format: Literal["parquet", "hdf5"] = "parquet"
    ):
        ...
    
    def start(self, duration: float, expected_frequency: float) -> None:
        """Begin recording. Pre-allocates buffers based on duration and frequency."""
        ...
    
    def stop(self) -> SignalLog:
        """Stop recording, flush buffers, return handle to persisted data."""
        ...

@dataclass
class SignalLog:
    """Handle to recorded signal data."""
    path: Path                         # Path to Parquet/HDF5 file
    signals: dict[str, SignalInfo]     # topic_name -> info (dtype, frequency, samples)
    duration: float
    start_time: float
    
    def get_signal(self, name: str) -> np.ndarray:
        """Load a single signal as numpy array. Columns: [timestamp, value]."""
        ...
    
    def get_signal_window(
        self, name: str, start: float, end: float
    ) -> np.ndarray:
        """Load signal data within a time window."""
        ...
```

### 4.6 Assertion Engine

**Core technical differentiator** over generic test tools. Every assertion operates on continuous time-series data and produces rich failure diagnostics.

#### 4.6.1 Predicate Interfaces

```python
# hrtf/assertions/predicates.py

@dataclass
class AssertionResult:
    """Result of evaluating a single assertion."""
    verdict: Literal["PASS", "FAIL"]
    assertion_type: str
    signal_name: str
    # Failure details (AS-06)
    first_violation_time: float | None
    violation_value: float | None
    expected_bound: float | None
    violation_duration: float | None
    # Context
    signal_summary: SignalSummary  # min, max, mean, std, final_value

class AssertionPredicate(ABC):
    """Base class for all signal assertions."""
    
    @abstractmethod
    def evaluate(self, signal: np.ndarray) -> AssertionResult:
        """
        Evaluate the predicate against signal data.
        
        Args:
            signal: 2D numpy array with columns [timestamp, value]
        
        Returns:
            AssertionResult with verdict and diagnostics
        """
        ...

class AlwaysAbove(AssertionPredicate):
    """Signal must remain above threshold for entire window (AS-02)."""
    
    def __init__(self, value: float, window: tuple[float, float]):
        self.value = value
        self.window = window
    
    def evaluate(self, signal: np.ndarray) -> AssertionResult:
        windowed = signal[
            (signal[:, 0] >= self.window[0]) & 
            (signal[:, 0] <= self.window[1])
        ]
        violations = windowed[windowed[:, 1] < self.value]
        
        if len(violations) == 0:
            return AssertionResult(verdict="PASS", ...)
        
        return AssertionResult(
            verdict="FAIL",
            assertion_type="always_above",
            signal_name=self.signal_name,
            first_violation_time=violations[0, 0],
            violation_value=violations[0, 1],
            expected_bound=self.value,
            violation_duration=violations[-1, 0] - violations[0, 0],
            ...
        )

class NeverExceeds(AssertionPredicate):
    """Signal must not exceed threshold at any point in window (AS-03)."""
    ...

class ReachesWithin(AssertionPredicate):
    """Signal must reach target value within tolerance before deadline (AS-04)."""
    ...

class StabilisesWithin(AssertionPredicate):
    """Signal variance must fall below tolerance within window (AS-05)."""
    
    def evaluate(self, signal: np.ndarray) -> AssertionResult:
        # Sliding window variance computation
        # Window size: 1 second (configurable)
        # Check if variance drops below tolerance^2 at any point in window
        ...

class EventOccurs(AssertionPredicate):
    """Discrete event must occur before deadline (AS-08)."""
    ...
```

#### 4.6.2 Compound Assertions (AS-07)

```python
# hrtf/assertions/compound.py

class CompoundAssertion(AssertionPredicate):
    """AND/OR combination of multiple predicates."""
    
    def __init__(
        self,
        operator: Literal["and", "or"],
        children: list[AssertionPredicate]
    ):
        self.operator = operator
        self.children = children
    
    def evaluate(self, signals: dict[str, np.ndarray]) -> AssertionResult:
        results = [child.evaluate(signals[child.signal_name]) for child in self.children]
        
        if self.operator == "and":
            passed = all(r.verdict == "PASS" for r in results)
        else:  # or
            passed = any(r.verdict == "PASS" for r in results)
        
        return AssertionResult(
            verdict="PASS" if passed else "FAIL",
            children=results,
            ...
        )
```

**YAML representation**:

```yaml
assertions:
  - type: "compound"
    operator: "and"
    children:
      - type: "always_above"
        signal: "/com_height"
        value: 0.75
        window: [5.0, 15.0]
      - type: "never_exceeds"
        signal: "/ankle_torque"
        value: 100.0
        window: [5.0, 15.0]
```

#### 4.6.3 Custom Assertion Registry (AS-09, v1.0)

```python
# Third-party assertion via entry point:
# [project.entry-points."hrtf.assertions"]
# my_assertion = "my_package:MyCustomAssertion"

# Or referenced from YAML:
assertions:
  - type: "custom"
    module: "my_package.assertions"
    class: "MyCustomAssertion"
    params:
      threshold: 0.5
```

### 4.7 Baseline Manager

```python
# hrtf/baselines/manager.py

@dataclass
class BaselineRecord:
    """A stored baseline reference."""
    name: str
    captured_from_run: str       # Run ID
    captured_at: datetime
    scenario_hash: str
    robot_hash: str
    metrics: dict[str, SignalSummary]  # Per-signal summary stats

@dataclass 
class RegressionReport:
    """Comparison result between a run and a baseline."""
    verdict: Literal["PASS", "REGRESSED"]
    baseline_name: str
    run_id: str
    per_metric: list[MetricDelta]
    tolerance: float

@dataclass
class MetricDelta:
    """Per-signal regression delta."""
    signal: str
    metric: str                  # "mean", "max", "std", etc.
    baseline_value: float
    current_value: float
    absolute_delta: float
    percentage_delta: float
    regressed: bool              # |percentage_delta| > tolerance

class BaselineManager:
    """Baseline capture, storage, and comparison (BL-01..BL-05)."""
    
    def __init__(self, store_path: Path = Path(".hrtf/baselines")):
        self.store_path = store_path
    
    def capture(self, run_id: str, name: str) -> BaselineRecord:
        """
        Extract summary statistics from a passing run and store as baseline.
        
        Stored as JSON files (BL-05):
          .hrtf/baselines/<name>/
            baseline.json        # Metadata + per-signal summary stats
            signals/             # Raw signal snapshots for overlay plots
        """
        ...
    
    def compare(
        self,
        run_id: str,
        baseline_name: str,
        tolerance: float = 0.05   # 5% default (BL-04)
    ) -> RegressionReport:
        """
        Compare run against baseline.
        
        For each signal in the baseline:
        1. Compute summary stats (mean, max, min, std, final_value) for current run
        2. Compute absolute and percentage delta vs baseline
        3. Flag REGRESSED if any metric exceeds tolerance
        
        Returns RegressionReport with per-metric detail (BL-03).
        """
        ...
    
    def list_baselines(self) -> list[BaselineRecord]:
        ...
```

**Baseline JSON format** (git-friendly, BL-05):

```json
{
  "hrtf_baseline_version": "1.0",
  "name": "v2.1-policy-stable",
  "captured_from_run": "run_20260401_143022",
  "captured_at": "2026-04-01T14:30:22Z",
  "scenario_hash": "sha256:abc123...",
  "robot_hash": "sha256:def456...",
  "simulator": "gazebo",
  "simulator_version": "Harmonic 8.x",
  "seed": 42,
  "metrics": {
    "/com_height": {
      "mean": 0.82,
      "min": 0.76,
      "max": 0.88,
      "std": 0.03,
      "final_value": 0.81
    },
    "/joint_torques/left_ankle": {
      "mean": 45.2,
      "min": 12.1,
      "max": 78.9,
      "std": 15.3,
      "final_value": 40.1
    }
  }
}
```

### 4.8 Report Generator

#### 4.8.1 JSON Report (RP-01)

```json
{
  "hrtf_result_version": "1.0",
  "run_id": "run_20260401_143022",
  "timestamp": "2026-04-01T14:30:22Z",
  "overall_verdict": "FAIL",
  "duration_wall_clock": 45.2,
  "evidence_manifest": {
    "scenario_yaml_hash": "sha256:abc...",
    "robot_urdf_hash": "sha256:def...",
    "simulator": "gazebo",
    "simulator_version": "Harmonic 8.1.0",
    "seed": 42,
    "hrtf_version": "0.1.0",
    "python_version": "3.10.12",
    "os": "Ubuntu 22.04.4 LTS"
  },
  "scenarios": [
    {
      "name": "Lateral Push Recovery",
      "source": "scenarios/push_recovery.yaml",
      "verdict": "FAIL",
      "sim_duration": 15.0,
      "wall_clock_duration": 32.1,
      "assertions": [
        {
          "type": "always_above",
          "signal": "/com_height",
          "verdict": "FAIL",
          "expected": "> 0.75 for [5.0, 15.0]",
          "first_violation_time": 5.42,
          "violation_value": 0.73,
          "violation_duration": 0.8
        }
      ],
      "signal_summary": {
        "/com_height": {"mean": 0.79, "min": 0.73, "max": 0.88, "std": 0.04}
      }
    }
  ]
}
```

#### 4.8.2 HTML Report (RP-02)

**Template**: Jinja2-based, self-contained single HTML file with embedded CSS/JS and inline base64-encoded plots.

**Structure**:
```
+--------------------------------------------------+
|  HRTF Test Report — Run run_20260401_143022       |
|  Overall: ❌ FAIL  |  2/3 passed  |  45.2s       |
+--------------------------------------------------+
|                                                    |
|  Scenario 1: Static Balance          ✅ PASS       |
|  ├── always_above /com_height > 0.75   ✅ PASS    |
|  └── [Signal Plot: CoM Height vs Time]            |
|                                                    |
|  Scenario 2: Lateral Push Recovery   ❌ FAIL       |
|  ├── always_above /com_height > 0.75   ❌ FAIL    |
|  │   First violation: t=5.42s, value=0.73m        |
|  ├── stabilises_within /com_height     ✅ PASS    |
|  └── [Signal Plot: CoM Height with violation zone]|
|                                                    |
|  Scenario 3: Flat Ground Gait        ✅ PASS       |
|  └── ...                                           |
|                                                    |
|  Evidence Manifest:                                |
|  URDF: sha256:def...  Scenario: sha256:abc...     |
|  Simulator: Gazebo Harmonic 8.1.0  Seed: 42      |
+--------------------------------------------------+
```

**Signal plots** (generated via Matplotlib):
- Time-series line plot per assertion signal
- Red shaded region for violation windows
- Dashed horizontal line for assertion threshold
- Vertical dashed line for disturbance application times

#### 4.8.3 PDF Report (RP-04)

Generated from the HTML report via **WeasyPrint** (pure Python, no browser dependency).

One-page executive summary followed by per-scenario detail pages.

#### 4.8.4 Report Generator Class

```python
# hrtf/reporting/json_report.py

class ReportGenerator:
    def generate(
        self,
        results: list[ScenarioResult],
        formats: list[Literal["json", "html", "pdf", "sarif"]],
        output_dir: Path,
        baseline_comparison: RegressionReport | None = None
    ) -> list[Path]:
        """Generate reports in requested formats. Returns output file paths."""
        outputs = []
        
        if "json" in formats:
            outputs.append(self._write_json(results, output_dir))
        if "html" in formats:
            plots = self._generate_plots(results)
            outputs.append(self._render_html(results, plots, output_dir))
        if "pdf" in formats:
            html_path = self._render_html(results, plots, output_dir)
            outputs.append(self._html_to_pdf(html_path, output_dir))
        if "sarif" in formats:
            outputs.append(self._write_sarif(results, output_dir))
        
        return outputs
```

### 4.9 CI/CD Integration

#### 4.9.1 Docker Image (CI-02)

```dockerfile
# docker/Dockerfile
FROM ros:humble-ros-base-jammy

# Install Gazebo Harmonic
RUN apt-get update && apt-get install -y \
    ros-humble-ros-gz \
    ros-humble-gz-sim \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install MuJoCo
RUN pip3 install mujoco

# Install HRTF
COPY . /opt/hrtf
RUN pip3 install /opt/hrtf

# Pre-download reference URDFs
RUN hrtf init --download-models

ENTRYPOINT ["hrtf"]
CMD ["--help"]
```

**Usage**:
```bash
# One-line run (CI-02)
docker run --rm -v $(pwd)/scenarios:/scenarios ghcr.io/hrtf/hrtf:latest \
    run /scenarios/my_test.yaml --sim gazebo --output-dir /scenarios/results
```

#### 4.9.2 GitHub Actions Template (CI-03)

```yaml
# ci/hrtf.yml
name: HRTF Robot Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/hrtf/hrtf:latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run HRTF scenarios
        run: |
          hrtf run scenarios/ \
            --sim gazebo \
            --workers 4 \
            --output-dir results/
      
      - name: Check for regressions
        run: |
          hrtf baseline compare results/run_latest baselines/stable \
            --tolerance 0.05
      
      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: hrtf-report
          path: results/
```

---

## 5. Data Models and Schemas

### 5.1 Core Data Classes

```python
# hrtf/core/types.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"       # Simulator crash or timeout (RB-03)
    SKIPPED = "SKIPPED"

@dataclass
class Pose:
    position: tuple[float, float, float]        # x, y, z
    orientation: tuple[float, float, float, float]  # quaternion x, y, z, w

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
class ScenarioResult:
    scenario_name: str
    scenario_source: Path
    scenario_hash: str
    verdict: Verdict
    sim_duration: float
    wall_clock_duration: float
    assertion_results: list[AssertionResult]
    signal_summaries: dict[str, SignalSummary]
    error_message: str | None = None
    stack_trace: str | None = None   # (RB-03)

@dataclass
class RunResult:
    run_id: str
    timestamp: datetime
    overall_verdict: Verdict
    scenarios: list[ScenarioResult]
    evidence_manifest: EvidenceManifest
    total_wall_clock: float

@dataclass
class EvidenceManifest:
    """Reproduction metadata (RP-05, SC-SEC-01)."""
    scenario_yaml_hash: str     # SHA-256
    robot_urdf_hash: str        # SHA-256
    simulator: str
    simulator_version: str
    seed: int
    hrtf_version: str
    python_version: str
    os_info: str
```

### 5.2 Result Store Layout

```
.hrtf/
  results/
    run_20260401_143022/
      result.json               # Full JSON result (RP-01)
      signals/
        com_height.parquet
        joint_torques.parquet
        base_velocity.parquet
      report.html               # HTML report (RP-02)
      summary.pdf               # PDF summary (RP-04)
  
  baselines/
    stable-v2.1/
      baseline.json
      signals/                  # Signal snapshots for overlay plots
    stable-v2.0/
      baseline.json
      signals/
  
  config.toml                   # User-level HRTF configuration
```

---

## 6. Built-in Scenario Library Design

Each built-in scenario (SC-01..SC-10) is a YAML file in `hrtf/scenario/library/` that works on any URDF-described bipedal robot through parameterized signal references.

### 6.1 Robot-Agnostic Signal Mapping

Built-in scenarios reference **logical signals** that are resolved at runtime via a robot-specific signal map:

```yaml
# hrtf/scenario/library/signal_maps/unitree_g1.yaml
signal_map:
  com_height: "/gz/unitree_g1/com_position/z"
  com_position: "/gz/unitree_g1/com_position"
  base_velocity: "/gz/unitree_g1/cmd_vel"
  joint_torques: "/gz/unitree_g1/joint_states/effort"
  zmp_x: "/gz/unitree_g1/zmp/x"
  zmp_y: "/gz/unitree_g1/zmp/y"
  estop: "/gz/unitree_g1/estop"
```

For unknown robots, HRTF auto-discovers standard ROS 2 topics (`sensor_msgs/JointState`, `geometry_msgs/PoseStamped`) and constructs the map. Users can override via `signal_map` in scenario YAML.

### 6.2 Canonical Scenario Specifications

| ID | Scenario File | Duration | Key Assertions |
|---|---|---|---|
| SC-01 | `static_balance.yaml` | 30s | `always_above(com_height, 0.75, [0,30])`, `always_within(zmp, support_polygon, [0,30])` |
| SC-02 | `lateral_push_recovery.yaml` | 15s | `always_above(com_height, 0.75, [5,15])`, impulse 50N at t=5s |
| SC-03 | `flat_ground_gait.yaml` | 12s | `reaches_within(base_x, 5.0, 0.1, 12)`, `always_above(com_height, 0.5, [0,12])` |
| SC-04 | `joint_torque_compliance.yaml` | 12s | `never_exceeds(joint_torques/*, rated_torque*0.95, [0,12])` — inherits SC-03 |
| SC-05 | `stair_ascent.yaml` | 20s | `always_increasing(com_z, [2,18])`, `reaches_within(step_3_contact, true, 20)` |
| SC-06 | `fall_detection_estop.yaml` | 10s | `event_occurs(estop, 0.1)` after forced CoM drop | 
| SC-07 | `payload_walking.yaml` | 12s | Extends SC-03, adds 5kg payload, `never_exceeds(torques, rated*0.90)` |
| SC-08 | `slope_ascent.yaml` | 15s | 10-degree incline, `reaches_within(base_x, 5.0, 0.2, 15)` |
| SC-09 | `object_grasp.yaml` | 15s | `event_occurs(grasp_success, 5)`, `always_above(grasp_force, 0.1, [5,15])` |
| SC-10 | `push_recovery_manipulation.yaml` | 20s | Compound: grasp maintained AND com_height > 0.75 during 30N push |

---

## 7. Simulation Determinism Strategy

Deterministic execution (SE-03, RB-01) is critical for meaningful regression testing. The strategy differs per adapter:

| Aspect | Gazebo Harmonic | MuJoCo |
|---|---|---|
| **Random seed** | `GZ_SIM_SEED` env var | Deterministic by default |
| **Time stepping** | Manual stepping via `/world/step` service (no wall-clock coupling) | `mj_step()` in Python loop |
| **Physics engine** | DART (default, deterministic) | MuJoCo engine (deterministic) |
| **Thread safety** | Single-threaded physics via paused + step mode | Single-threaded Python loop |
| **Floating point** | Controlled via `GZ_SIM_PHYSICS_ENGINE_THREAD_POOL=1` | No thread pool; fully sequential |
| **Verification** | Run SC-01 twice with same seed, assert bit-identical signal logs | Same approach |

**CI verification**: A dedicated test `test_determinism.py` runs each adapter twice with the same seed and asserts numpy array equality on all signal channels.

---

## 8. Error Handling Strategy

### 8.1 Exception Hierarchy

```python
# hrtf/core/exceptions.py

class HRTFError(Exception):
    """Base exception for all HRTF errors."""
    pass

class HRTFModelError(HRTFError):
    """Robot model loading or validation failure."""
    diagnostics: list[ValidationDiagnostic]

class HRTFScenarioError(HRTFError):
    """Scenario YAML parsing or validation failure."""
    file_path: Path
    line_number: int | None
    suggestion: str | None

class HRTFAdapterError(HRTFError):
    """Simulator adapter setup or communication failure."""
    adapter_name: str

class HRTFSimulatorCrash(HRTFAdapterError):
    """Simulator process crashed during execution (RB-03)."""
    exit_code: int
    stderr: str

class HRTFTimeoutError(HRTFError):
    """Scenario exceeded wall-clock timeout."""
    timeout_seconds: float
    sim_time_reached: float

class HRTFAssertionError(HRTFError):
    """Assertion evaluation failure (not assertion FAIL — internal error)."""
    pass

class HRTFBaselineError(HRTFError):
    """Baseline not found or incompatible."""
    pass
```

### 8.2 Error Reporting (UX-03, UX-04)

All user-facing errors follow the pattern:

```
ERROR: <what went wrong>
  File: <path>:<line>
  Fix:  <actionable suggestion>
```

Assertion failures (UX-04):

```
FAIL: always_above — /com_height dropped below threshold
  Signal:    /com_height
  Expected:  > 0.75 m for window [5.0s, 15.0s]
  Actual:    0.73 m at t=5.42s (violated for 0.8s)
  Context:   Disturbance applied at t=5.0s (50N lateral impulse)
```

### 8.3 Simulator Crash Recovery (RB-02, RB-03)

```python
# hrtf/execution/recovery.py

class CrashRecoveryHandler:
    """
    Handles simulator crashes gracefully.
    
    On crash:
    1. Catch the subprocess exit / connection error
    2. Capture full stack trace and stderr
    3. Mark scenario verdict = ERROR (never PASS or FAIL)
    4. Write partial results to result store
    5. Continue with next scenario (RB-02: no corruption)
    """
    
    MAX_RETRIES = 1  # Retry once on crash (RB-04, v1.0)
    
    def handle_crash(
        self, scenario: ScenarioConfig, error: HRTFSimulatorCrash
    ) -> ScenarioResult:
        return ScenarioResult(
            scenario_name=scenario.name,
            verdict=Verdict.ERROR,
            error_message=f"Simulator crashed with exit code {error.exit_code}",
            stack_trace=error.stderr,
            ...
        )
```

---

## 9. Testing Strategy

### 9.1 Test Pyramid

```
         /\
        /  \     E2E: Full scenario runs in Docker (Gazebo + MuJoCo)
       /    \    ~10 tests, run in CI nightly
      /------\
     /        \   Integration: Adapter + Logger + Assertions on live sim
    /          \  ~30 tests, run on every PR
   /------------\
  /              \  Unit: Parser, assertions, baseline manager, report gen
 /                \ ~200 tests, run on every commit
/==================\
```

### 9.2 Unit Tests (no simulator required)

| Module | Test Focus |
|---|---|
| `test_loader.py` | URDF parsing, validation diagnostics, malformed input handling |
| `test_scenario_parser.py` | YAML parsing, schema validation, inheritance, parameterization |
| `test_assertions.py` | Each predicate with synthetic numpy signal data |
| `test_baseline_manager.py` | Capture, compare, tolerance logic, edge cases |
| `test_report_generator.py` | JSON schema compliance, HTML structure, PDF generation |

### 9.3 Integration Tests (simulator required)

| Test | What It Verifies |
|---|---|
| `test_gazebo_adapter.py` | Gazebo launches, URDF loads, disturbance applies, signals received |
| `test_mujoco_adapter.py` | MuJoCo loads URDF, steps physics, publishes telemetry |
| `test_determinism.py` | Two identical runs produce bit-identical signals |
| `test_full_run.py` | End-to-end: YAML in, JSON/HTML report out, correct exit code |

### 9.4 Scenario Validation Tests

Each built-in scenario (SC-01..SC-10) has a golden-result test that verifies it produces the expected verdict on the reference Unitree G1 URDF.

---

## 10. Deployment Architecture

### 10.1 Package Distribution

```
PyPI:  pip install hrtf              # Core framework + MuJoCo adapter
       pip install hrtf[gazebo]      # Adds Gazebo dependencies
       pip install hrtf[isaac]       # Adds Isaac Sim dependencies (v1.0)
       pip install hrtf[all]         # Everything
       pip install hrtf[matlab]      # Adds .mat export (scipy)

Docker: ghcr.io/hrtf/hrtf:latest    # Ubuntu 22.04 + ROS 2 + Gazebo + MuJoCo
        ghcr.io/hrtf/hrtf:humble    # Pinned to ROS 2 Humble
        ghcr.io/hrtf/hrtf:jazzy     # Pinned to ROS 2 Jazzy
```

### 10.2 Entry Points

```toml
# pyproject.toml
[project.scripts]
hrtf = "hrtf.cli.main:cli"

[project.entry-points."hrtf.adapters"]
gazebo = "hrtf.adapters.gazebo:GazeboHarmonicAdapter"
mujoco = "hrtf.adapters.mujoco:MuJoCoAdapter"

[project.entry-points."hrtf.assertions"]
# Built-in assertions registered here; third-party plugins add their own
```

---

## 11. Phased Implementation Plan

### Phase 1: MVP Demo (Months 0-3)

| Sprint | Deliverables | Req IDs |
|---|---|---|
| **1-2** | Project scaffolding, CLI skeleton (`hrtf run`, `hrtf init`), URDF loader with validation, scenario YAML parser with JSON Schema validation | RL-01..03, SA-01..04, CI-01 |
| **3-4** | MuJoCo adapter (simpler — no external process), signal logger, 4 core assertion predicates (`always_above`, `never_exceeds`, `reaches_within`, `stabilises_within`) | SE-02, SE-03, AS-01..06 |
| **5-6** | Gazebo Harmonic adapter, determinism verification, compound assertions | SE-01, SE-03, AS-07..08 |
| **7-8** | Scenarios SC-01..SC-05 on Unitree G1, JSON + HTML reports, baseline capture/compare | SA-05, BL-01..04, RP-01..03 |
| **9-10** | Docker image, GitHub Actions template, quickstart docs, integration tests | CI-02..03, UX-01..05 |
| **11-12** | Bug fixes, performance tuning (PF-01), parallel execution (SE-04), PDF report (RP-04) | SE-04, PF-01, RP-04 |

**MVP Demo Gate**: SC-01 through SC-05 all pass on Unitree G1 URDF in Docker container.

### Phase 2: MVP Complete (Months 3-5)

| Deliverable | Req IDs |
|---|---|
| Scenarios SC-06..SC-10 | SA-05 |
| SDF format support | RL-04 |
| Scenario inheritance | SA-06 |
| Git-compatible baseline storage | BL-05 |
| Evidence manifest in reports | RP-05 |
| SHA-256 integrity hashing | SC-SEC-01 |
| Public GitHub repo with CI | All |

**MVP Complete Gate**: Two external engineers run quickstart independently in < 30 min.

### Phase 3: v1.0 Product (Months 6-12)

| Deliverable | Req IDs |
|---|---|
| Isaac Sim adapter | SE-06 |
| Custom assertion entry points | AS-09, EX-02 |
| Custom scenario types | EX-03 |
| Named test suites | SA-07 |
| Signal overlay plots (current vs baseline) | BL-07 |
| Automatic baseline promotion | BL-06 |
| SARIF output | RP-06 |
| Requirements traceability matrix | RP-07 |
| Simulink .mat export | EX-05 |
| GitLab CI support | CI-04 |
| Slack/Teams webhooks | CI-05 |
| Signed Docker images + SBOM | SC-SEC-02 |

### Phase 4: v2.0 Vision (Months 12-24)

| Deliverable | Req IDs |
|---|---|
| Hardware-in-the-loop execution | SE-07 |
| Cloud-parallel executor | SE-08 |
| Temporal logic assertions (LTL/MTL) | AS-10 |
| Fleet-level baseline aggregation | BL-08 |
| ISO 25785-1 compliance package | RP-08 |
| Visual scenario editor (web UI) | SA-08 |
| Browser-based result explorer | UX-06 |
| Parametric robot families | RL-07 |
| Result caching by hash | CI-06 |

---

## 12. Design Decisions and Trade-offs

| Decision | Alternatives Considered | Rationale |
|---|---|---|
| **Click for CLI** | argparse, Typer | Click has mature subcommand support, automatic `--help`, and wide adoption. Typer adds unnecessary type annotation overhead for this use case. |
| **Parquet for signal storage** | HDF5, CSV, SQLite | Parquet is columnar (fast signal-level reads), compressed, and integrates natively with pandas/numpy. HDF5 offered as fallback for MATLAB compatibility. |
| **Jinja2 + WeasyPrint for reports** | Pandoc, ReportLab, browser-based PDF | Pure Python stack with no browser dependency. WeasyPrint renders CSS faithfully for consistent output across machines. |
| **Subprocess isolation per scenario** | Threads, asyncio | Simulator crashes in one scenario must not affect others (RB-02). Subprocess boundaries provide OS-level isolation. Minor overhead is acceptable. |
| **JSON Schema for YAML validation** | Pydantic-only, custom parser | JSON Schema is a published standard. Users can validate scenario YAML with any JSON Schema tool, not just HRTF. Pydantic used internally after schema validation for typed access. |
| **Entry points for plugins** | Plugin directories, importlib hooks | Entry points are the standard Python plugin mechanism. Supported by pip, poetry, and setuptools. No custom discovery code needed. |
| **Manual stepping for Gazebo determinism** | Real-time factor=0, lock-step | Manual stepping via service call is the only guaranteed way to decouple physics from wall clock. Real-time factor=0 still allows timing jitter. |
| **ROS 2 as integration backbone** | Custom IPC, ZeroMQ | The target audience already uses ROS 2. Using ROS 2 topics for telemetry means HRTF works with any ROS 2-based robot stack without adaptation. |

---

## 13. Appendix: Requirement Traceability

| Req ID | Design Component | Section |
|---|---|---|
| RL-01..07 | Robot Model Loader | 4.2 |
| SA-01..08 | Scenario Engine | 4.3 |
| SE-01..08 | Simulation Adapter Layer | 4.4 |
| AS-01..10 | Signal Logger + Assertion Engine | 4.5, 4.6 |
| BL-01..08 | Baseline Manager | 4.7 |
| RP-01..08 | Report Generator | 4.8 |
| CI-01..06 | CI/CD Integration | 4.9 |
| SC-01..10 | Built-in Scenario Library | 6 |
| PF-01..05 | Execution Orchestrator, Signal Logger | 4.5, Process Architecture |
| RB-01..04 | Determinism Strategy, Error Handling | 7, 8 |
| UX-01..06 | CLI Layer, Error Handling | 4.1, 8.2 |
| EX-01..05 | Adapter Registry, Assertion Registry | 4.4.4, 4.6.3, 10.2 |
| SC-SEC-01..03 | Evidence Manifest, Docker, Data Handling | 5.1, 10.1 |

---

*End of Design Document*
*HRTF — Humanoid Robot Test Framework | Design Document v1.0 | April 2026*
