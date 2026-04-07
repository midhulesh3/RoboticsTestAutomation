from streamlit.testing.v1 import AppTest

def test_app_loads():
    at = AppTest.from_file("hrtf/ui/app.py").run()
    assert not at.exception
    assert "Humanoid Robot Test Framework" in at.title[0].value

def test_navigation():
    at = AppTest.from_file("hrtf/ui/app.py").run()
    assert not at.exception

    # By default, it's on "Run Test"
    assert at.header[0].value == "Run Test"

    # Change to "Fixtures"
    at.sidebar.radio[0].set_value("Fixtures").run()
    assert at.header[0].value == "Fixtures"

    # Change to "View Reports"
    at.sidebar.radio[0].set_value("View Reports").run()
    assert at.header[0].value == "View Reports"

def test_empty_states(monkeypatch):
    import hrtf.ui.app as app
    from pathlib import Path

    # Mock directories to point to non-existent ones to force empty state
    monkeypatch.setattr(app, "FIXTURES_DIR", Path("non_existent_dir"))
    monkeypatch.setattr(app, "TEST_CASES_DIR", Path("non_existent_dir"))
    monkeypatch.setattr(app, "RUN_SETTINGS_DIR", Path("non_existent_dir"))
    monkeypatch.setattr(app, "SCENARIOS_DIR", Path("non_existent_dir"))
    monkeypatch.setattr(app, "RESULTS_DIR", Path("non_existent_dir"))

    at = AppTest.from_file("hrtf/ui/app.py").run()
    assert not at.exception

def test_execution_ui():
    at = AppTest.from_file("hrtf/ui/app.py").run()
    assert not at.exception

    # By default it's on "Run Test"
    # Ensure there are dropdowns
    assert len(at.selectbox) >= 3

    # We won't simulate a full click because it runs a long-running sub-process or sim that might fail
    # We will just assert that the structure is there
    assert at.button[0].label == "🚀 Run Test"
