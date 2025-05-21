# Guardian Evaluation UI - Usage Guide

The Guardian Evaluation System provides a simple web interface for inputting transaction data, running the guardian evaluation process, and viewing the results. This guide will walk you through how to use the system.

## Installation

Before you can use the Guardian Evaluation UI, you need to install the required dependencies:

1. Make sure you have Python 3.10 or higher installed.
2. Run the installation script:
```bash
./install_ui.sh
```

Alternatively, you can install manually:
```bash
pip install uv
uv pip install -e .
```

## Running the UI

To start the UI, run one of the following commands:

```bash
python -m tamo_junto.run_ui
```

Or if you've installed the package:

```bash
run_ui
```

This will launch a Streamlit web application that you can access in your browser (typically at http://localhost:8501).

## Using the UI

### 1. Input Transaction Details

On the main screen, you'll see a form with the following fields:

- **Topic**: The general subject area (default: "AI LLMs")
- **Transaction Hash**: The transaction identifier (default: "0x123...")
- **Current Year**: The current year (automatically populated)
- **Request Reason**: The reason for the disclosure request (default: "Suspicious transaction pattern detected")

You can also add **Additional Custom Inputs** in JSON format if needed.

### 2. Evaluate the Transaction

Click the "Evaluate Transaction" button to start the guardian evaluation process.

### 3. View the Thinking Process

The UI has two tabs:

- **Thinking Process**: Shows the real-time thinking of the guardian agents as they evaluate the transaction
- **Results**: Displays the final evaluation outcome and the complete guardian report

## Understanding the Results

The evaluation process involves multiple "guardian" agents:

1. **Regulatory Compliance Guardian**: Evaluates from a regulatory perspective
2. **Financial Institution Risk Guardian**: Assesses institutional risk
3. **Digital Privacy Guardian**: Focuses on privacy implications
4. **Impartial Oversight Guardian**: Provides objective assessment
5. **Guardian Response Collator**: Compiles all guardians' inputs into a final report

Each guardian votes YES/NO/ABSTAIN on the disclosure request with detailed justification.

## Customizing Default Inputs

You can modify the default input values by editing the file:
```
src/tamo_junto/config/inputs.py
```

## Troubleshooting

- If you encounter errors, check the "guardian_evaluation.log" file for details
- Ensure your OpenAI API key is properly configured in the .env file
- For more detailed debugging, check the Streamlit logs in the terminal

## Support

For additional support or questions, please refer to the main README.md file or contact the project maintainers. 