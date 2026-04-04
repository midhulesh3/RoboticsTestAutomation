import pytest
from pathlib import Path
from hrtf.models.loader import RobotModelLoader
from hrtf.core.exceptions import HRTFModelError

VALID_URDF = b"""
<robot name="test_robot">
    <link name="base_link">
        <inertial>
            <mass value="1.0" />
        </inertial>
    </link>
    <link name="arm_link">
        <inertial>
            <mass value="0.5" />
        </inertial>
    </link>
    <joint name="base_to_arm" type="revolute">
        <limit lower="-1.0" upper="1.0" effort="10.0" velocity="5.0" />
    </joint>
</robot>
"""

INVALID_XML_URDF = b"<robot><link></robot>"

MISSING_LINK_URDF = b"<robot name='test_robot'></robot>"

NEGATIVE_MASS_URDF = b"""
<robot name="test_robot">
    <link name="base_link">
        <inertial>
            <mass value="-1.0" />
        </inertial>
    </link>
</robot>
"""

BAD_LIMITS_URDF = b"""
<robot name="test_robot">
    <link name="base_link">
        <inertial>
            <mass value="1.0" />
        </inertial>
    </link>
    <joint name="bad_joint" type="revolute">
        <limit lower="1.0" upper="-1.0" />
    </joint>
</robot>
"""

@pytest.fixture
def temp_urdf(tmp_path):
    def _create_urdf(content: bytes) -> Path:
        p = tmp_path / "robot.urdf"
        p.write_bytes(content)
        return p
    return _create_urdf

def test_load_valid_urdf(temp_urdf):
    path = temp_urdf(VALID_URDF)
    loader = RobotModelLoader()
    model = loader.load(path)

    assert model.name == "test_robot"
    assert len(model.links) == 2
    assert model.links[0].name == "base_link"
    assert model.links[0].mass == 1.0
    assert len(model.joints) == 1
    assert model.joints[0].name == "base_to_arm"
    assert "base_to_arm" in model.joint_limits
    assert model.joint_limits["base_to_arm"].lower == -1.0

def test_load_invalid_xml(temp_urdf):
    path = temp_urdf(INVALID_XML_URDF)
    loader = RobotModelLoader()
    with pytest.raises(HRTFModelError) as exc:
        loader.load(path)
    assert any("XML parse error" in d.message for d in exc.value.diagnostics)

def test_load_missing_links(temp_urdf):
    path = temp_urdf(MISSING_LINK_URDF)
    loader = RobotModelLoader()
    with pytest.raises(HRTFModelError) as exc:
        loader.load(path)
    assert any("No links found" in d.message for d in exc.value.diagnostics)

def test_load_negative_mass(temp_urdf):
    path = temp_urdf(NEGATIVE_MASS_URDF)
    loader = RobotModelLoader()
    with pytest.raises(HRTFModelError) as exc:
        loader.load(path)
    assert any("negative mass" in d.message for d in exc.value.diagnostics)

def test_load_bad_limits(temp_urdf):
    path = temp_urdf(BAD_LIMITS_URDF)
    loader = RobotModelLoader()
    with pytest.raises(HRTFModelError) as exc:
        loader.load(path)
    assert any("lower_limit > upper_limit" in d.message for d in exc.value.diagnostics)
