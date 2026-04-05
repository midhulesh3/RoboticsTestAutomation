import streamlit as st
import json
import pandas as pd
from pathlib import Path

from hrtf.execution.orchestrator import ExecutionOrchestrator
from hrtf.baselines.manager import BaselineManager

st.set_page_config(page_title="HRTF Dashboard", layout="wide")

st.title("Humanoid Robot Test Framework")

# Basic Sidebar Navigation
page = st.sidebar.radio("Navigation", ["Run Scenarios", "View Reports", "Baselines"])

if page == "Run Scenarios":
    st.header("Run Scenarios")
    st.write("Select a scenario to run it in the local MuJoCo adapter.")

    scenarios_dir = Path("scenarios")
    if scenarios_dir.exists():
        yaml_files = list(scenarios_dir.glob("*.yaml"))
    else:
        yaml_files = []

    if yaml_files:
        selected_scenario = st.selectbox("Select Scenario", yaml_files, format_func=lambda x: x.name)

        col1, col2 = st.columns(2)
        with col1:
            simulator = st.selectbox("Simulator", ["mujoco", "gazebo", "isaac_sim"])
        with col2:
            seed = st.number_input("Random Seed", value=42)

        if st.button("Run", type="primary"):
            with st.spinner(f"Running {selected_scenario.name}..."):
                orchestrator = ExecutionOrchestrator()
                # Override the simulator backend with the selected one
                overrides = {"simulator.backend": simulator, "simulator.seed": str(seed)}
                result = orchestrator.run_scenario(selected_scenario, param_overrides=overrides)

                if result.verdict == "PASS":
                    st.success("Scenario Passed!")
                elif result.verdict == "FAIL":
                    st.error("Scenario Failed.")
                else:
                    st.warning(f"Scenario Error: {result.error_message}")

                st.subheader("Assertions")
                if result.assertion_results:
                    for a in result.assertion_results:
                        if a.verdict == "PASS":
                            st.write(f"✅ **{a.assertion_type}** on `{a.signal_name}`")
                        else:
                            st.write(f"❌ **{a.assertion_type}** on `{a.signal_name}` - Expected: {a.expected_bound}")
                else:
                    st.info("No assertions were run.")
    else:
        st.info("No scenario files found. Create a 'scenarios/' directory with .yaml files.")

elif page == "View Reports":
    st.header("View Reports")

    results_dir = Path("results")
    if results_dir.exists():
        json_files = list(results_dir.glob("*.json"))
    else:
        json_files = []

    if json_files:
        selected_report = st.selectbox("Select Report", json_files, format_func=lambda x: x.name)

        try:
            data = json.loads(selected_report.read_text())
            st.subheader(f"Run: {data.get('run_id')}")

            verdict = data.get('overall_verdict')
            if verdict == "PASS":
                st.success("Overall Verdict: PASS")
            else:
                st.error(f"Overall Verdict: {verdict}")

            st.write(f"**Date:** {data.get('timestamp')}")
            st.write(f"**Duration:** {data.get('total_wall_clock'):.2f} seconds")

            for s in data.get('scenarios', []):
                with st.expander(f"Scenario: {s.get('scenario_name')}"):
                    if s.get("error_message"):
                        st.warning(f"Error: {s.get('error_message')}")

                    st.write("**Signal Summaries**")
                    summaries = s.get("signal_summaries", {})
                    if summaries:
                        # Convert to DataFrame for a nice table
                        df_data = []
                        for sig, stat in summaries.items():
                            row = {"Signal": sig}
                            row.update(stat)
                            df_data.append(row)
                        st.dataframe(pd.DataFrame(df_data))

                        st.write("**Plots**")
                        # Basic bar charts from the summary data using Streamlit native charts
                        for sig, stat in summaries.items():
                            st.write(sig)
                            chart_data = pd.DataFrame(
                                [stat['mean'], stat['min'], stat['max'], stat['final_value']],
                                index=["mean", "min", "max", "final"],
                                columns=["Value"]
                            )
                            st.bar_chart(chart_data)
        except Exception as e:
            st.error(f"Failed to load report: {e}")
    else:
        st.info("No reports found in the 'results/' directory.")

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
                    st.write(f"📦 {b}")
            else:
                st.info("No baselines stored.")
        else:
            st.info("No baselines directory found.")

    with col2:
        st.subheader("Capture New Baseline")
        results_dir = Path("results")
        if results_dir.exists():
            json_files = list(results_dir.glob("*.json"))
            if json_files:
                run_id_to_capture = st.selectbox("Select Run", json_files, format_func=lambda x: x.stem)
                new_baseline_name = st.text_input("Baseline Name")

                if st.button("Capture Baseline"):
                    if new_baseline_name:
                        try:
                            manager.capture(run_id_to_capture.stem, new_baseline_name, results_dir=results_dir)
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
