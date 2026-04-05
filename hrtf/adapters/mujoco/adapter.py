try:
    import mujoco
    HAS_MUJOCO = True
except ImportError:
    HAS_MUJOCO = False

import numpy as np
from typing import Any
from pathlib import Path
from hrtf.adapters.base import SimulatorAdapter
from hrtf.core.types import RobotModel, Pose, DisturbanceProfile
from hrtf.signals.logger import SignalLogger


class MuJoCoAdapter(SimulatorAdapter):
    """Adapter for MuJoCo physics simulation."""

    def __init__(self, logger: SignalLogger | None = None):
        self._model: Any = None
        self._data: Any = None
        self._logger = logger
        self._step_size = 0.002
        self._disturbances: list[DisturbanceProfile] = []
        self._initial_pose: Pose | None = None

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        self._model = None
        self._data = None
        self._disturbances.clear()

    def load_robot(self, model: RobotModel, pose: Pose) -> None:
        if not HAS_MUJOCO:
            raise RuntimeError("MuJoCo is not installed.")

        # Prefer MJCF (.xml) if it exists alongside the URDF — it includes ground plane
        model_path = model.urdf_path
        mjcf_path = model_path.with_suffix(".xml")
        if mjcf_path.exists():
            model_path = mjcf_path

        try:
            self._model = mujoco.MjModel.from_xml_path(str(model_path))
        except Exception as e:
            raise RuntimeError(f"Failed to load MuJoCo model: {e}")

        self._data = mujoco.MjData(self._model)
        self._initial_pose = pose

        # Set initial position if the model has a free joint (nq >= 7 means freejoint root)
        if self._model.nq >= 7:
            # Free joint: qpos[0:3] = position, qpos[3:7] = quaternion (w,x,y,z)
            self._data.qpos[0] = pose.position[0]
            self._data.qpos[1] = pose.position[1]
            self._data.qpos[2] = pose.position[2]
            # MuJoCo quaternion is (w, x, y, z); scenario orientation is (x, y, z, w)
            ox, oy, oz, ow = pose.orientation
            self._data.qpos[3] = ow
            self._data.qpos[4] = ox
            self._data.qpos[5] = oy
            self._data.qpos[6] = oz

        # Forward kinematics to update derived quantities
        mujoco.mj_forward(self._model, self._data)

    def configure(self, seed: int, step_size: float, real_time_factor: float) -> None:
        self._step_size = step_size
        if self._model:
            self._model.opt.timestep = step_size

    def apply_disturbance(self, disturbance: DisturbanceProfile) -> None:
        self._disturbances.append(disturbance)

    def _find_body_id(self, link_name: str) -> int:
        """Resolve a URDF link name to a MuJoCo body id."""
        try:
            return mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, link_name)
        except Exception:
            # Fallback: try the root body (id=1, since 0 is world)
            return min(1, self._model.nbody - 1)

    def _apply_step_disturbances(self, current_time: float) -> None:
        """Apply all active disturbances for the current timestep."""
        for dist in self._disturbances:
            body_id = self._find_body_id(dist.link)

            if dist.type == "impulse":
                end_time = dist.time + (dist.duration or self._step_size)
                if dist.time <= current_time < end_time and dist.force:
                    # xfrc_applied is (nbody, 6): [fx, fy, fz, tx, ty, tz]
                    self._data.xfrc_applied[body_id, 0] = dist.force[0]
                    self._data.xfrc_applied[body_id, 1] = dist.force[1]
                    self._data.xfrc_applied[body_id, 2] = dist.force[2]
                elif current_time >= end_time:
                    # Clear force after impulse window
                    self._data.xfrc_applied[body_id, :3] = 0.0

            elif dist.type == "static_load":
                if current_time >= dist.time:
                    # Static load: constant downward gravitational force from added mass
                    gravity_z = self._model.opt.gravity[2]  # typically -9.81
                    added_force = (dist.mass or 0.0) * gravity_z
                    self._data.xfrc_applied[body_id, 2] = added_force

            elif dist.type == "sinusoidal":
                if current_time >= dist.time and dist.force:
                    freq = 1.0 / (dist.duration or 1.0)
                    scale = np.sin(2.0 * np.pi * freq * (current_time - dist.time))
                    self._data.xfrc_applied[body_id, 0] = dist.force[0] * scale
                    self._data.xfrc_applied[body_id, 1] = dist.force[1] * scale
                    self._data.xfrc_applied[body_id, 2] = dist.force[2] * scale

    def _log_signals(self, current_time: float) -> None:
        """Log all available telemetry signals at the current timestep."""
        if not self._logger:
            return

        # CoM height — use subtree_com of the root body if available
        if self._model.nbody > 1:
            # subtree_com for root body (id 1, since 0 is world) gives whole-robot CoM
            com = self._data.subtree_com[1]
            self._logger.log("/com_height", current_time, float(com[2]))
            self._logger.log("/com_x", current_time, float(com[0]))
            self._logger.log("/com_y", current_time, float(com[1]))
        elif self._model.nq >= 3:
            self._logger.log("/com_height", current_time, float(self._data.qpos[2]))

        # Joint positions, velocities, and torques (actuator forces)
        for i in range(self._model.njnt):
            joint_name = mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_JOINT, i)
            if joint_name is None:
                joint_name = f"joint_{i}"

            joint_type = self._model.jnt_type[i]
            # Skip free joints (type 0) — those are logged as CoM
            if joint_type == 0:
                continue

            qpos_adr = self._model.jnt_qposadr[i]
            qvel_adr = self._model.jnt_dofadr[i]

            self._logger.log(f"/joint/{joint_name}/position", current_time, float(self._data.qpos[qpos_adr]))
            self._logger.log(f"/joint/{joint_name}/velocity", current_time, float(self._data.qvel[qvel_adr]))

        # Actuator forces (torques)
        for i in range(self._model.nu):
            act_name = mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            if act_name is None:
                act_name = f"actuator_{i}"
            self._logger.log(f"/actuator/{act_name}/force", current_time, float(self._data.actuator_force[i]))

        # Contact forces — total normal force
        total_contact_force = 0.0
        for i in range(self._data.ncon):
            contact = self._data.contact[i]
            c_force = np.zeros(6)
            mujoco.mj_contactForce(self._model, self._data, i, c_force)
            total_contact_force += abs(c_force[0])  # normal force
        self._logger.log("/contact/total_normal_force", current_time, float(total_contact_force))

        # Base link velocity (if free joint exists)
        if self._model.nq >= 7:
            self._logger.log("/base/linear_velocity_x", current_time, float(self._data.qvel[0]))
            self._logger.log("/base/linear_velocity_y", current_time, float(self._data.qvel[1]))
            self._logger.log("/base/linear_velocity_z", current_time, float(self._data.qvel[2]))
            self._logger.log("/base/angular_velocity_x", current_time, float(self._data.qvel[3]))
            self._logger.log("/base/angular_velocity_y", current_time, float(self._data.qvel[4]))
            self._logger.log("/base/angular_velocity_z", current_time, float(self._data.qvel[5]))

    def run(self, duration: float) -> None:
        if not self._model or not self._data:
            raise RuntimeError("Model not loaded")

        steps = int(duration / self._step_size)
        if self._logger:
            self._logger.start(duration, 1.0 / self._step_size)

        for step in range(steps):
            current_time = step * self._step_size

            self._apply_step_disturbances(current_time)
            mujoco.mj_step(self._model, self._data)
            self._log_signals(current_time)

        if self._logger:
            self._logger.stop()

    def get_signal_sources(self) -> list[str]:
        sources = ["/com_height", "/com_x", "/com_y", "/contact/total_normal_force"]
        if self._model:
            for i in range(self._model.njnt):
                name = mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_JOINT, i)
                if name and self._model.jnt_type[i] != 0:
                    sources.extend([
                        f"/joint/{name}/position",
                        f"/joint/{name}/velocity",
                    ])
            for i in range(self._model.nu):
                name = mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
                if name:
                    sources.append(f"/actuator/{name}/force")
        return sources

    @property
    def name(self) -> str:
        return "MuJoCo"

    @property
    def version(self) -> str:
        if HAS_MUJOCO:
            return mujoco.__version__
        return "unknown"
