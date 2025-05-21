#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path

# Ensure the module is in the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def main():
    """Entry point for running the UI via the command line."""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Use subprocess to run Streamlit directly
    cmd = ["streamlit", "run", os.path.join(current_dir, "ui.py")]
    subprocess.run(cmd)

# Run directly if this script is executed
if __name__ == "__main__":
    main() 