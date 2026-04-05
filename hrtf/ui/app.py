import streamlit as st
import json
import uuid
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime

from hrtf.execution.orchestrator import ExecutionOrchestrator
from hrtf.scenario.composer import compose
from hrtf.baselines.manager import BaselineManager

st.set_page_config(page_title="HRTF Dashboard", layout="wide")

st.title("Humanoid Robot Test Framework")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path("fixtures")
TEST_CASES_DIR = Path("test_cases")
RUN_SETTINGS_DIR = Path("run_settings")
SCENARIOS_DIR = Path("scenarios")
RESULTS_DIR = Path("results")


def _list_yamls(directory: Path) -> list[Path]:
    if directory.exists():
        return sorted(directory.glob("*.yaml"))
    return []


def _read_yaml_name(path: Path) -> str:
    """Read the human-readable name from a YAML file."""
    try:
        data = yaml.safe_load(path.read_text())
        for root_key in ("fixture", "test_case", "run_settings", "scenario"):
            if root_key in data:
                return data[root_key].get("name", path.stem)
        return path.stem
    except Exception:
        return path.stem


def _save_result(result) -> Path:
    """Save a ScenarioResult to the results directory and return the path."""
    RESULTS_DIR.mkdir(exist_ok=True)
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "overall_verdict": result.verdict.value,
        "total_wall_clock": result.wall_clock_duration,
        "scenarios": [
            {
                "scenario_name": result.scenario_name,
                "verdict": result.verdict.value,
                "sim_duration": result.sim_duration,
                "wall_clock_duration": result.wall_clock_duration,
                "error_message": result.error_message,
                "signal_summaries": {
                    sig: {
                        "mean": s.mean,
                        "min": s.min,
                        "max": s.max,
                        "std": s.std,
                        "final_value": s.final_value,
                        "sample_count": s.sample_count,
                    }
                    for sig, s in result.signal_summaries.items()
                },
                "assertion_results": [
                    {
                        "assertion_type": a.assertion_type,
                        "signal_name": a.signal_name,
                        "verdict": a.verdict.value,
                        "expected_bound": a.expected_bound,
                        "violation_value": a.violation_value,
                    }
                    for a in result.assertion_results
                ],
            }
        ],
    }
    report_path = RESULTS_DIR / f"{run_id}.json"
    report_path.write_text(json.dumps(report, indent=2))
    return report_path


def _show_result(result):
    """Display a ScenarioResult in the UI."""
    if result.verdict.value == "PASS":
        st.success(f"**{result.verdict.value}** — {result.scenario_name}")
    elif result.verdict.value == "FAIL":
        st.error(f"**{result.verdict.value}** — {result.scenario_name}")
    else:
        st.warning(f"**{result.verdict.value}** — {result.error_message}")

    if result.assertion_results:
        for a in result.assertion_results:
            if a.verdict.value == "PASS":
                st.write(f"  :white_check_mark: **{a.assertion_type}** on `{a.signal_name}`")
            else:
                detail = ""
                if a.violation_value is not None:
                    detail = f" (got {a.violation_value:.4f}, bound {a.expected_bound})"
                st.write(f"  :x: **{a.assertion_type}** on `{a.signal_name}`{detail}")
    else:
        st.info("No assertions were evaluated.")

    st.caption(f"Wall-clock: {result.wall_clock_duration:.2f}s | Sim duration: {result.sim_duration}s")


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

page = st.sidebar.radio(
    "Navigation",
    ["Run Test", "Fixtures", "Test Cases", "Run Settings", "Legacy Scenarios", "View Reports", "Baselines"],
)

# ---------------------------------------------------------------------------
# Page: Run Test  (fixture + test case + run settings)
# ---------------------------------------------------------------------------

if page == "Run Test":
    st.header("Run Test")
    st.write("Compose a test run by selecting a **fixture**, **test case**, and **run settings**.")

    fixture_files = _list_yamls(FIXTURES_DIR)
    test_case_files = _list_yamls(TEST_CASES_DIR)
    run_settings_files = _list_yamls(RUN_SETTINGS_DIR)

    if not fixture_files:
        st.info("No fixtures found. Add `.yaml` files to the `fixtures/` directory.")
    elif not test_case_files:
        st.info("No test cases found. Add `.yaml` files to the `test_cases/` directory.")
    elif not run_settings_files:
        st.info("No run settings found. Add `.yaml` files to the `run_settings/` directory.")
    else:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Fixture")
            selected_fixture = st.selectbox(
                "Robot setup",
                fixture_files,
                format_func=lambda p: _read_yaml_name(p),
                key="fixture_select",
            )
            with st.expander("Fixture details"):
                st.code(selected_fixture.read_text(), language="yaml")

        with col2:
            st.subheader("Test Case")
            selected_test_case = st.selectbox(
                "What to test",
                test_case_files,
                format_func=lambda p: _read_yaml_name(p),
                key="test_case_select",
            )
            with st.expander("Test case details"):
                st.code(selected_test_case.read_text(), language="yaml")

        with col3:
            st.subheader("Run Settings")
            selected_run_settings = st.selectbox(
                "Simulator config",
                run_settings_files,
                format_func=lambda p: _read_yaml_name(p),
                key="run_settings_select",
            )
            with st.expander("Run settings details"):
                st.code(selected_run_settings.read_text(), language="yaml")

        st.divider()

        if st.button("Run Test", type="primary", use_container_width=True):
            with st.spinner("Composing and executing..."):
                try:
                    config = compose(selected_fixture, selected_test_case, selected_run_settings)
                    orchestrator = ExecutionOrchestrator()
                    result = orchestrator.run_composed(config)

                    _show_result(result)

                    report_path = _save_result(result)
                    st.caption(f"Report saved: `{report_path}`")

                except Exception as e:
                    st.error(f"Error: {e}")

# ---------------------------------------------------------------------------
# Page: Fixtures
# ---------------------------------------------------------------------------

elif page == "Fixtures":
    st.header("Fixtures")
    st.write("Simulator-agnostic robot setups: model, pose, and initial joint positions.")

    fixture_files = _list_yamls(FIXTURES_DIR)
    if fixture_files:
        for f in fixture_files:
            name = _read_yaml_name(f)
            with st.expander(f"{name}  (`{f.name}`)"):
                st.code(f.read_text(), language="yaml")
    else:
        st.info("No fixtures found. Add `.yaml` files to `fixtures/`.")

# ---------------------------------------------------------------------------
# Page: Test Cases
# ---------------------------------------------------------------------------

elif page == "Test Cases":
    st.header("Test Cases")
    st.write("Simulator-agnostic test definitions: disturbances, assertions, and pass/fail criteria.")

    test_case_files = _list_yamls(TEST_CASES_DIR)
    if test_case_files:
        for tc in test_case_files:
            name = _read_yaml_name(tc)
            with st.expander(f"{name}  (`{tc.name}`)"):
                st.code(tc.read_text(), language="yaml")
    else:
        st.info("No test cases found. Add `.yaml` files to `test_cases/`.")

# ---------------------------------------------------------------------------
# Page: Run Settings
# ---------------------------------------------------------------------------

elif page == "Run Settings":
    st.header("Run Settings")
    st.write("Simulator-specific configuration: backend, seed, step size.")

    run_settings_files = _list_yamls(RUN_SETTINGS_DIR)
    if run_settings_files:
        for rs in run_settings_files:
            name = _read_yaml_name(rs)
            with st.expander(f"{name}  (`{rs.name}`)"):
                st.code(rs.read_text(), language="yaml")
    else:
        st.info("No run settings found. Add `.yaml` files to `run_settings/`.")

# ---------------------------------------------------------------------------
# Page: Legacy Scenarios (monolithic YAML — backward compat)
# ---------------------------------------------------------------------------

elif page == "Legacy Scenarios":
    st.header("Legacy Scenarios")
    st.write("Run monolithic scenario YAML files (fixture + test + settings in one file).")

    yaml_files = _list_yamls(SCENARIOS_DIR)

    if yaml_files:
        selected_scenario = st.selectbox(
            "Select Scenario", yaml_files, format_func=lambda x: _read_yaml_name(x)
        )

        with st.expander("Scenario YAML"):
            st.code(selected_scenario.read_text(), language="yaml")

        if st.button("Run", type="primary"):
            with st.spinner(f"Running {selected_scenario.name}..."):
                orchestrator = ExecutionOrchestrator()
                result = orchestrator.run_scenario(selected_scenario)

                _show_result(result)

                report_path = _save_result(result)
                st.caption(f"Report saved: `{report_path}`")
    else:
        st.info("No scenario files found in `scenarios/`.")

# ---------------------------------------------------------------------------
# Page: View Reports
# ---------------------------------------------------------------------------

elif page == "View Reports":
    st.header("View Reports")

    if RESULTS_DIR.exists():
        json_files = sorted(RESULTS_DIR.glob("*.json"), reverse=True)
    else:
        json_files = []

    if json_files:
        selected_report = st.selectbox(
            "Select Report", json_files, format_func=lambda x: x.name
        )

        try:
            data = json.loads(selected_report.read_text())
            st.subheader(f"Run: {data.get('run_id')}")

            verdict = data.get("overall_verdict")
            if verdict == "PASS":
                st.success("Overall Verdict: PASS")
            else:
                st.error(f"Overall Verdict: {verdict}")

            st.write(f"**Date:** {data.get('timestamp')}")
            st.write(f"**Duration:** {data.get('total_wall_clock', 0):.2f} seconds")

            for s in data.get("scenarios", []):
                with st.expander(f"Scenario: {s.get('scenario_name')}"):
                    if s.get("error_message"):
                        st.warning(f"Error: {s.get('error_message')}")

                    # Assertion results table
                    assertions = s.get("assertion_results", [])
                    if assertions:
                        st.write("**Assertions**")
                        for a in assertions:
                            icon = ":white_check_mark:" if a["verdict"] == "PASS" else ":x:"
                            st.write(f"{icon} **{a['assertion_type']}** on `{a['signal_name']}` — {a['verdict']}")

                    # Signal summaries
                    summaries = s.get("signal_summaries", {})
                    if summaries:
                        st.write("**Signal Summaries**")
                        df_data = []
                        for sig, stat in summaries.items():
                            row = {"Signal": sig}
                            row.update(stat)
                            df_data.append(row)
                        st.dataframe(pd.DataFrame(df_data))

                        for sig, stat in summaries.items():
                            st.write(f"**{sig}**")
                            chart_data = pd.DataFrame(
                                [stat["mean"], stat["min"], stat["max"], stat["final_value"]],
                                index=["mean", "min", "max", "final"],
                                columns=["Value"],
                            )
                            st.bar_chart(chart_data)
        except Exception as e:
            st.error(f"Failed to load report: {e}")
    else:
        st.info("No reports found in `results/`.")

# ---------------------------------------------------------------------------
# Page: Baselines
# ---------------------------------------------------------------------------

elif page == "Baselines":
    st.header("Baselines")

    baselines_dir = Path(".hrtf/baselines")
    manager = BaselineManager(store_path=baselines_dir)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Stored Baselines")
        if baselines_dir.exists():
            baselines = [d.name for d in baselines_dir.iterdir() if d.is_dir()]
            if baselines:
                for b in baselines:
                    st.write(f":package: {b}")
            else:
                st.info("No baselines stored.")
        else:
            st.info("No baselines directory found.")

    with col2:
        st.subheader("Capture New Baseline")
        if RESULTS_DIR.exists():
            json_files = sorted(RESULTS_DIR.glob("*.json"), reverse=True)
            if json_files:
                run_id_to_capture = st.selectbox(
                    "Select Run", json_files, format_func=lambda x: x.stem
                )
                new_baseline_name = st.text_input("Baseline Name")

                if st.button("Capture Baseline"):
                    if new_baseline_name:
                        try:
                            manager.capture(
                                run_id_to_capture.stem,
                                new_baseline_name,
                                results_dir=RESULTS_DIR,
                            )
                            st.success(f"Captured {new_baseline_name} successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to capture: {e}")
                    else:
                        st.warning("Please provide a baseline name.")
            else:
                st.info("No runs available to capture.")
        else:
            st.info("No runs available to capture.")
