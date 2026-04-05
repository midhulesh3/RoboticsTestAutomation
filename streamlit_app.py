# This file is used by Streamlit Community Cloud to run the app.
import os
import sys
import subprocess

if __name__ == "__main__":
    # Ensure the hrtf package is installed
    try:
        import hrtf
    except ImportError:
        print("HRTF module not found, installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])

    # Launch the Streamlit app
    app_path = os.path.join(os.path.dirname(__file__), "hrtf", "ui", "app.py")
    sys.exit(subprocess.call(["streamlit", "run", app_path]))
