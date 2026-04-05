# This file is used by Streamlit Community Cloud to run the app
import subprocess
import sys

# Try to run the module directly
try:
    from hrtf.ui.app import *
except ImportError:
    print("HRTF module not found, attempting to run via subprocess or install.")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
    from hrtf.ui.app import *
