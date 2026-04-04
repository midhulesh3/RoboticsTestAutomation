import xml.etree.ElementTree as ET
from pathlib import Path
import hashlib

from hrtf.core.types import RobotModel, ValidationDiagnostic, JointInfo, LinkInfo, JointLimits
from hrtf.core.exceptions import HRTFModelError

class RobotModelLoader:
    """Load and validate robot models from URDF."""

    def load(self, source: str | Path) -> RobotModel:
        """Load from a URDF file path."""
        path = Path(source)
        if not path.exists():
            raise HRTFModelError(f"URDF file not found: {path}")

        with open(path, "rb") as f:
            content = f.read()
        urdf_hash = hashlib.sha256(content).hexdigest()

        diagnostics = self._validate_urdf(path, content)
        errors = [d for d in diagnostics if d.severity == "error"]
        if errors:
            raise HRTFModelError("URDF validation failed", diagnostics)

        tree = ET.fromstring(content)
        robot_name = tree.attrib.get("name", "unknown")

        joints = []
        joint_limits = {}
        for joint in tree.findall("joint"):
            j_name = joint.attrib.get("name", "")
            j_type = joint.attrib.get("type", "fixed")
            joints.append(JointInfo(name=j_name, type=j_type))

            limit = joint.find("limit")
            if limit is not None:
                try:
                    lower = float(limit.attrib.get("lower", 0.0))
                    upper = float(limit.attrib.get("upper", 0.0))
                    eff = float(limit.attrib.get("effort", 0.0))
                    vel = float(limit.attrib.get("velocity", 0.0))
                    joint_limits[j_name] = JointLimits(lower, upper, eff, vel)
                except ValueError:
                    pass

        links = []
        for link in tree.findall("link"):
            l_name = link.attrib.get("name", "")
            mass = 0.0
            inertial = link.find("inertial")
            if inertial is not None:
                mass_node = inertial.find("mass")
                if mass_node is not None:
                    try:
                        mass = float(mass_node.attrib.get("value", 0.0))
                    except ValueError:
                        pass
            links.append(LinkInfo(name=l_name, mass=mass))

        return RobotModel(
            name=robot_name,
            urdf_path=path,
            urdf_hash=urdf_hash,
            format="urdf",
            joints=joints,
            links=links,
            joint_limits=joint_limits
        )

    def _validate_urdf(self, path: Path, content: bytes) -> list[ValidationDiagnostic]:
        diagnostics = []
        try:
            tree = ET.fromstring(content)
        except ET.ParseError as e:
            diagnostics.append(ValidationDiagnostic(
                severity="error", element="xml", line_number=None,
                message=f"XML parse error: {e}", suggestion="Ensure URDF is valid XML."
            ))
            return diagnostics

        if tree.tag != "robot":
            diagnostics.append(ValidationDiagnostic(
                severity="error", element="robot", line_number=None,
                message="Root element must be <robot>", suggestion="Wrap your model in a <robot> tag."
            ))

        if not tree.findall("link"):
            diagnostics.append(ValidationDiagnostic(
                severity="error", element="link", line_number=None,
                message="No links found", suggestion="Add at least one <link>."
            ))

        for link in tree.findall("link"):
            name = link.attrib.get("name", "unnamed")
            inertial = link.find("inertial")
            if inertial is not None:
                mass_node = inertial.find("mass")
                if mass_node is not None:
                    try:
                        mass = float(mass_node.attrib.get("value", "0.0"))
                        if mass == 0.0:
                            diagnostics.append(ValidationDiagnostic(
                                severity="warning", element="mass", line_number=None,
                                message=f"Link '{name}' has zero mass.", suggestion="Set a small positive mass."
                            ))
                        elif mass < 0.0:
                            diagnostics.append(ValidationDiagnostic(
                                severity="error", element="mass", line_number=None,
                                message=f"Link '{name}' has negative mass.", suggestion="Mass must be non-negative."
                            ))
                    except ValueError:
                        pass

        for joint in tree.findall("joint"):
            name = joint.attrib.get("name", "unnamed")
            limit = joint.find("limit")
            if limit is not None:
                try:
                    lower = float(limit.attrib.get("lower", "0.0"))
                    upper = float(limit.attrib.get("upper", "0.0"))
                    if lower > upper:
                        diagnostics.append(ValidationDiagnostic(
                            severity="error", element="limit", line_number=None,
                            message=f"Joint '{name}' has lower_limit > upper_limit",
                            suggestion="Swap the lower and upper limit values."
                        ))
                except ValueError:
                    pass

        return diagnostics
