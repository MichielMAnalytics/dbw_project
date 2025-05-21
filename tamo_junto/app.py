import streamlit as st
import json
import io
import sys
import logging
from typing import Dict, Any
import os
import traceback
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import from the installed tamo_junto package
from tamo_junto.crew import TamoJunto
from tamo_junto.config.inputs import get_default_inputs

# Configure logging to capture both file and stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('guardian_evaluation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Log the API key status (don't log the actual key!)
if os.environ.get("OPENAI_API_KEY"):
    logger.info("OPENAI_API_KEY is set in environment")
else:
    logger.warning("OPENAI_API_KEY is not set in environment")

class StreamCapture:
    """Capture stdout to display in Streamlit"""
    def __init__(self, st_container):
        self.st_container = st_container
        self.buffer = io.StringIO()
        self.stdout = sys.stdout
        self.output_text = ""
        self.auto_update = True
        # Create a placeholder for output
        self.output_placeholder = st_container.empty()
        
    def __enter__(self):
        sys.stdout = self
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.stdout
        
    def write(self, text):
        self.buffer.write(text)
        self.stdout.write(text)
        
        # Accumulate text
        self.output_text += text
        
        # Update the display if auto update is enabled
        if self.auto_update:
            # Clear and update the placeholder with current text
            self.output_placeholder.empty()
            
            # Use markdown for display (no key required)
            formatted_output = f"```\n{self.output_text}\n```"
            self.output_placeholder.markdown(formatted_output)
            
            # Check for important messages in the last few lines
            last_lines = self.output_text.split('\n')[-10:]  # Get last 10 lines
            last_text = '\n'.join(last_lines)
            
            if any(marker in last_text for marker in ["🤖 Agent:", "└── 🤖 Agent:", "Task output"]):
                self.st_container.markdown("---")
                self.st_container.markdown(f"**Important Update:**\n```\n{last_text}\n```")
        
    def flush(self):
        self.stdout.flush()
        
    def toggle_updates(self):
        """Toggle automatic updates of the UI"""
        self.auto_update = not self.auto_update
        return self.auto_update

def main():
    st.set_page_config(
        page_title="Guardian Evaluation System",
        page_icon="🛡️",
        layout="wide"
    )
    
    st.title("🛡️ Guardian Evaluation System")
    st.write("Input transaction details and view the guardian evaluation process and results")
    
    # Display API key status (without showing the key)
    if os.environ.get("OPENAI_API_KEY"):
        st.success("✅ OpenAI API key is configured")
    else:
        st.error("❌ OpenAI API key is not configured. Please check your .env file.")
        st.info("Create a .env file in the tamo_junto directory with the following content: OPENAI_API_KEY=your_api_key_here")
        return
    
    # Get default inputs
    default_inputs = get_default_inputs()
    
    # Create a form for user input
    with st.form(key="input_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            topic = st.text_input("Topic", value=default_inputs.get("topic", ""))
            transaction_hash = st.text_input("Transaction Hash", value=default_inputs.get("transaction_hash", ""))
        
        with col2:
            current_year = st.text_input("Current Year", value=default_inputs.get("current_year", str(datetime.now().year)))
            request_reason = st.text_area("Request Reason", value=default_inputs.get("request_reason", ""))
        
        # Additional custom inputs
        st.subheader("Additional Custom Inputs (JSON Format)")
        custom_inputs_str = st.text_area("Custom Inputs (JSON)", value="{}", height=150)
        
        submit_button = st.form_submit_button(label="Evaluate Transaction")
    
    if submit_button:
        try:
            # Parse custom inputs
            custom_inputs = json.loads(custom_inputs_str)
            
            # Combine default and custom inputs
            inputs = {
                "topic": topic,
                "current_year": current_year,
                "transaction_hash": transaction_hash,
                "request_reason": request_reason,
                **custom_inputs
            }
            
            st.write("### Input Parameters")
            st.json(inputs)
            
            # Create a tab layout for thinking process and results
            tab1, tab2 = st.tabs(["Thinking Process", "Results"])
            
            with tab1:
                thinking_container = st.container()
                
                # Add a button to toggle auto-updates if needed
                if 'capture' in locals():
                    if st.button("Toggle Auto-Updates"):
                        auto_update_enabled = capture.toggle_updates()
                        st.write(f"Auto-updates: {'Enabled' if auto_update_enabled else 'Disabled'}")
                
                # Capture stdout to display the thinking process
                with StreamCapture(thinking_container) as capture:
                    # Initialize the crew
                    logger.info("Initializing the crew...")
                    crew = TamoJunto().crew()
                    
                    # Set up verbose mode to see thinking process
                    logger.info("Starting Guardian Evaluation...")
                    
                    try:
                        # Run the crew with the inputs and verbose mode
                        result = crew.kickoff(inputs=inputs)
                        
                        with tab2:
                            # Display the final result
                            st.write("### Guardian Evaluation Result")
                            st.markdown(result)
                            
                            # If final_guardian_report.md exists, display it
                            if os.path.exists("final_guardian_report.md"):
                                with open("final_guardian_report.md", "r") as f:
                                    report_content = f.read()
                                st.write("### Final Guardian Report")
                                st.markdown(report_content)
                    except Exception as e:
                        st.error(f"An error occurred while running the evaluation: {str(e)}")
                        st.error(traceback.format_exc())
            
        except json.JSONDecodeError:
            st.error("Error: Invalid JSON format in custom inputs.")

if __name__ == "__main__":
    main() 