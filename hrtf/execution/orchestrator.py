import time
from pathlib import Path

from hrtf.core.types import ScenarioResult, Verdict, ScenarioConfig
from hrtf.scenario.parser import ScenarioParser
from hrtf.models.loader import RobotModelLoader
from hrtf.adapters.base import SimulatorAdapter
from hrtf.signals.logger import SignalLogger
from hrtf.assertions.engine import AssertionEngine

def get_adapter(backend: str, logger: SignalLogger) -> SimulatorAdapter:
    if backend == "mujoco":
        from hrtf.adapters.mujoco.adapter import MuJoCoAdapter
        return MuJoCoAdapter(logger=logger)
    else:
        raise ValueError(f"Unsupported backend: {backend}")

class ExecutionOrchestrator:
    """Orchestrates scenario execution."""

    def __init__(self):
        self.parser = ScenarioParser()
        self.loader = RobotModelLoader()
        self.assertion_engine = AssertionEngine()

    def run_scenario(self, scenario_path: Path, param_overrides: dict[str, str] | None = None) -> ScenarioResult:
        """Run from a monolithic scenario YAML file."""
        config = self.parser.parse(scenario_path, param_overrides)
        return self._execute(config, scenario_path.parent)

    def run_composed(self, config: ScenarioConfig) -> ScenarioResult:
        """Run from a pre-composed ScenarioConfig (fixture + test case + run settings)."""
        # For composed configs, robot paths are relative to the project root
        return self._execute(config, Path("."))

    def _execute(self, config: ScenarioConfig, base_dir: Path) -> ScenarioResult:
        start_time = time.time()

        try:
            # Use real paths if absolute, else relative to base_dir
            urdf_path = config.robot_source
            if not Path(urdf_path).is_absolute() and "test_robot" not in urdf_path:
                 urdf_path = base_dir / urdf_path

            robot_model = self.loader.load(urdf_path)

            logger = SignalLogger()
            adapter = get_adapter(config.simulator_backend, logger)

            adapter.setup()
            adapter.load_robot(robot_model, config.initial_conditions.pose)
            adapter.configure(config.seed, config.step_size, config.real_time_factor)

            for dist in config.disturbances:
                adapter.apply_disturbance(dist)

            adapter.run(config.duration)
            log = logger.stop()
            adapter.teardown()

            assertion_results = self.assertion_engine.evaluate(log, config.assertions)

            all_passed = all(r.verdict == Verdict.PASS for r in assertion_results)
            verdict = Verdict.PASS if all_passed and assertion_results else Verdict.FAIL
            if not assertion_results:
                verdict = Verdict.PASS

            end_time = time.time()

            signal_summaries = {}
            for res in assertion_results:
                if res.signal_summary and res.signal_name:
                    signal_summaries[res.signal_name] = res.signal_summary

            return ScenarioResult(
                scenario_name=config.name,
                scenario_source=config.source_path,
                scenario_hash=config.source_hash,
                verdict=verdict,
                sim_duration=config.duration,
                wall_clock_duration=end_time - start_time,
                assertion_results=assertion_results,
                signal_summaries=signal_summaries
            )

        except Exception as e:
            return ScenarioResult(
                scenario_name=config.name if config else str(base_dir),
                scenario_source=config.source_path if config else "",
                scenario_hash="",
                verdict=Verdict.ERROR,
                sim_duration=0.0,
                wall_clock_duration=time.time() - start_time,
                assertion_results=[],
                signal_summaries={},
                error_message=str(e)
            )
