# HRTF Next Steps

The MVP has been initialized.

To resume development in the next session, you should implement the following modules defined in the `HRTF_Design_Document_v1.0.md`:

1.  **Robot Model Loader (`hrtf/models/loader.py`)**
    *   Implement loading and structural validation of URDF/SDF files as described in Section 4.2.
    *   Surface actionable errors using `HRTFModelError`.
2.  **Simulation Adapter Layer (`hrtf/adapters/`)**
    *   Define the `SimulatorAdapter` abstract base class (Section 4.4.1).
    *   Start implementing the MuJoCo adapter (`hrtf/adapters/mujoco/adapter.py`) as it's simpler (in-process).
3.  **Signal Logger (`hrtf/signals/logger.py`)**
    *   Implement high-performance ROS 2 telemetry logger (Section 4.5).
4.  **Assertion Engine (`hrtf/assertions/`)**
    *   Implement the core time-series assertions (`always_above`, `never_exceeds`, etc.) as defined in Section 4.6.
5.  **Expand Tests**
    *   Write tests for the Robot Model Loader and Assertion Engine predicates using `pytest`.

Ensure you verify functionality frequently using standard `pytest` unit tests!
