import mujoco
from typing import Any
from pathlib import Path
from hrtf.adapters.base import SimulatorAdapter
from hrtf.core.types import RobotModel, Pose, DisturbanceProfile
from hrtf.signals.logger import SignalLogger

class MuJoCoAdapter(SimulatorAdapter):
    """Adapter for MuJoCo."""

    def __init__(self, logger: SignalLogger | None = None):
        self._model: Any = None
        self._data: Any = None
        self._logger = logger
        self._step_size = 0.002
        self._disturbances: list[DisturbanceProfile] = []

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass

    def load_robot(self, model: RobotModel, pose: Pose) -> None:
        try:
            self._model = mujoco.MjModel.from_xml_path(str(model.urdf_path))
        except Exception as e:
            raise RuntimeError(f"Failed to load MuJoCo model: {e}")

        self._data = mujoco.MjData(self._model)

    def configure(self, seed: int, step_size: float, real_time_factor: float) -> None:
        self._step_size = step_size
        if self._model:
            self._model.opt.timestep = step_size

    def apply_disturbance(self, disturbance: DisturbanceProfile) -> None:
        self._disturbances.append(disturbance)

    def run(self, duration: float) -> None:
        if not self._model or not self._data:
            raise RuntimeError("Model not loaded")

        steps = int(duration / self._step_size)
        if self._logger:
            self._logger.start(duration, 1.0 / self._step_size)

        for step in range(steps):
            current_time = step * self._step_size

            # Apply scheduled disturbances
            for dist in self._disturbances:
                if dist.type == "impulse" and dist.time <= current_time < dist.time + (dist.duration or self._step_size):
                    # In a real implementation we would map dist.link to body id and apply force
                    pass

            mujoco.mj_step(self._model, self._data)

            if self._logger:
                # Log com_height as an example
                try:
                    com_height = self._data.qpos[2]  # typically z position for root joint
                    self._logger.log("/com_height", current_time, com_height)
                except IndexError:
                    pass

        if self._logger:
            self._logger.stop()

    def get_signal_sources(self) -> list[str]:
        return ["/com_height", "/joint_states"]

    @property
    def name(self) -> str:
        return "MuJoCo"

    @property
    def version(self) -> str:
        return "3.6.0"
