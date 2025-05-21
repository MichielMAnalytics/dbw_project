#!/bin/bash

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "UV not found, installing..."
    pip install uv
fi

# Install the project dependencies
echo "Installing project dependencies..."
uv pip install -e .

# Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

echo "Installation complete! You can now run the UI with:"
echo "python -m tamo_junto.run_ui"
echo "or"
echo "run_ui (if installed via pip)" 