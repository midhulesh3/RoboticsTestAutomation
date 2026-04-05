# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HRTF (Humanoid Robot Test Framework) is a Python 3.10+ CLI tool for testing and validating humanoid robot systems across simulation backends (MuJoCo, Gazebo, Isaac Sim). It uses YAML-based scenario files that define robot models, initial conditions, disturbances, and assertions to validate robot behavior. Includes a Streamlit web dashboard.

## Common Commands

```bash
# Install (editable)
pip install -e .

# Run all tests
pytest

# Run a single test file
pytest tests/test_parser.py

# Run only unit tests
pytest tests/unit/

# Run integration tests (requires MuJoCo)
pytest tests/integration/

# CLI usage
hrtf init my_robot.urdf --scenario-type balance --output scenarios/my_test.yaml
hrtf run scenarios/my_test.yaml --sim mujoco
hrtf baseline capture <run_id> my_stable_baseline
hrtf report <run_id>

# Launch Streamlit dashboard
hrtf ui
```

## Architecture

The execution pipeline flows: **CLI -> ScenarioParser -> RobotModelLoader -> SimulatorAdapter -> SignalLogger -> AssertionEngine -> ScenarioResult**.

- **`hrtf/cli/`**: Click-based CLI with subcommands (`run`, `init`, `baseline`, `report`, `ui`). Entry point: `hrtf.cli.main:cli`.
- **`hrtf/scenario/parser.py`**: Parses YAML scenario files, validates against JSON schema (`hrtf/scenario/schema/scenario_v1.json`), produces `ScenarioConfig`.
- **`hrtf/execution/orchestrator.py`**: Central orchestrator that wires parsing, model loading, simulation, signal logging, and assertion evaluation together. `ExecutionOrchestrator.run_scenario()` is the main entry point for running a test.
- **`hrtf/adapters/base.py`**: `SimulatorAdapter` ABC defining the interface all sim backends must implement (`setup`, `load_robot`, `configure`, `apply_disturbance`, `run`, `teardown`). MuJoCo adapter is in `hrtf/adapters/mujoco/adapter.py`.
- **`hrtf/assertions/`**: `AssertionEngine` dispatches to predicate classes (`AlwaysAbove`, `NeverExceeds`, `ReachesWithin`, `StabilisesWithin`) and supports compound assertions with AND/OR operators.
- **`hrtf/signals/logger.py`**: `SignalLogger` records telemetry during simulation; produces a `SignalLog` for assertion evaluation.
- **`hrtf/models/loader.py`**: Loads and parses URDF robot model files into `RobotModel` dataclasses.
- **`hrtf/core/types.py`**: All core dataclasses (`ScenarioConfig`, `ScenarioResult`, `RunResult`, `Verdict`, etc.). Note: "Assertion" is spelled "Assertion" throughout the codebase (in class names like `AssertionResult`, `AssertionSpec`, `AssertionEngine`).
- **`streamlit_app.py`**: Entry point for Streamlit Cloud deployment; `hrtf/ui/app.py` contains the dashboard logic.

## Key Design Details

- MuJoCo is conditionally imported (`python_version < '3.14'`). Integration tests skip when MuJoCo is unavailable. Any new sim adapter code should handle optional imports similarly.
- Scenario files use a `scenario:` root key with nested `robot`, `simulator`, `initial_conditions`, `disturbance`, `duration`, and `assertions` sections.
- Simulator adapters are registered as entry points in `pyproject.toml` under `hrtf.adapters`.
- The `Verdict` enum has four states: `PASS`, `FAIL`, `ERROR`, `SKIPPED`.
