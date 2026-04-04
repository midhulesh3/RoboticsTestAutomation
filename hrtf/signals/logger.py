import numpy as np
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SignalInfo:
    dtype: str
    frequency: float
    samples: int

@dataclass
class SignalLog:
    path: Path | None
    signals: dict[str, SignalInfo]
    duration: float
    start_time: float
    _data: dict[str, list[tuple[float, float]]]

    def get_signal(self, name: str) -> np.ndarray:
        if name not in self._data:
            return np.array([])
        return np.array(self._data[name])

class SignalLogger:
    """Basic in-memory signal logger for MVP."""

    def __init__(self):
        self._data: dict[str, list[tuple[float, float]]] = {}
        self._is_recording = False
        self._duration = 0.0

    def start(self, duration: float, expected_frequency: float) -> None:
        self._is_recording = True
        self._duration = duration
        self._data.clear()

    def log(self, topic: str, timestamp: float, value: float) -> None:
        if not self._is_recording:
            return
        if topic not in self._data:
            self._data[topic] = []
        self._data[topic].append((timestamp, value))

    def stop(self) -> SignalLog:
        self._is_recording = False
        signals_info = {}
        for topic, data in self._data.items():
            signals_info[topic] = SignalInfo(
                dtype="float64",
                frequency=len(data)/self._duration if self._duration > 0 else 0,
                samples=len(data)
            )

        return SignalLog(
            path=None,
            signals=signals_info,
            duration=self._duration,
            start_time=0.0,
            _data=dict(self._data)
        )
