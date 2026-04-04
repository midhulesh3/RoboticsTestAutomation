from pathlib import Path

class HRTFError(Exception):
    """Base exception for all HRTF errors."""
    pass

class HRTFModelError(HRTFError):
    """Robot model loading or validation failure."""
    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics or []

class HRTFScenarioError(HRTFError):
    """Scenario YAML parsing or validation failure."""
    def __init__(self, message, file_path=None, line_number=None, suggestion=None):
        super().__init__(message)
        self.file_path = file_path
        self.line_number = line_number
        self.suggestion = suggestion

class HRTFAdapterError(HRTFError):
    """Simulator adapter setup or communication failure."""
    def __init__(self, message, adapter_name=None):
        super().__init__(message)
        self.adapter_name = adapter_name

class HRTFSimulatorCrash(HRTFAdapterError):
    """Simulator process crashed during execution."""
    def __init__(self, message, adapter_name=None, exit_code=None, stderr=None):
        super().__init__(message, adapter_name)
        self.exit_code = exit_code
        self.stderr = stderr

class HRTFTimeoutError(HRTFError):
    """Scenario exceeded wall-clock timeout."""
    def __init__(self, message, timeout_seconds=None, sim_time_reached=None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.sim_time_reached = sim_time_reached

class HRTFAssertionError(HRTFError):
    """Assertion evaluation failure."""
    pass

class HRTFBaselineError(HRTFError):
    """Baseline not found or incompatible."""
    pass
