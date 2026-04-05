# HRTF - Humanoid Robot Test Framework

The Humanoid Robot Test Framework (HRTF) is a Python 3.10+ CLI tool built with Click, designed to test and validate humanoid robot systems across simulation backends like Gazebo, MuJoCo, and Isaac Sim. It now also features a **Streamlit Web Dashboard** for easily running and reviewing scenarios.

## Installation

1. Create a virtual environment and install the dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

2. Or install directly via the `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Local CLI

To generate a boilerplate scenario file:
```bash
hrtf init my_robot.urdf --scenario-type balance --output scenarios/my_test.yaml
```

To run a scenario file:
```bash
hrtf run scenarios/my_test.yaml --sim mujoco
```

To capture a successful run as a baseline:
```bash
hrtf baseline capture <run_id> my_stable_baseline
```

To compare a recent run against a baseline:
```bash
hrtf baseline compare <run_id> my_stable_baseline --tolerance 0.05
```

To generate an HTML report:
```bash
hrtf report <run_id>
```

### Streamlit Web Dashboard

To launch the UI locally to run scenarios, manage baselines, and view reports visually:
```bash
hrtf ui
# Or alternatively:
streamlit run streamlit_app.py
```

### Cloud Deployment (Streamlit Community Cloud)

This project is configured to deploy directly to Streamlit Community Cloud.
1. Connect your repository to [share.streamlit.io](https://share.streamlit.io).
2. Point the "Main file path" to `streamlit_app.py`.
3. Deploy!
