from abc import ABC, abstractmethod
from hrtf.core.types import RobotModel, Pose, DisturbanceProfile

class SimulatorAdapter(ABC):
    """Abstract interface for simulation back-ends."""

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
    def configure(self, seed: int, step_size: float, real_time_factor: float) -> None:
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
    def get_signal_sources(self) -> list[str]:
        """Return available telemetry signal sources (topics, channels)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Simulator version string."""
        ...
