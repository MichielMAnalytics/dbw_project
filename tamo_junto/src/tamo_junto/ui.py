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

# Fix imports by using relative imports
from ..tamo_junto.crew import TamoJunto
from ..tamo_junto.config.inputs import get_default_inputs

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

class StreamCapture:
    """Capture stdout to display in Streamlit"""
    def __init__(self, st_container):
        self.st_container = st_container
        self.buffer = io.StringIO()
        self.stdout = sys.stdout
        self.thinking_output = ""
        
    def __enter__(self):
        sys.stdout = self
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.stdout
        
    def write(self, text):
        self.buffer.write(text)
        self.stdout.write(text)
        
        # Extract thinking process or agent outputs
        if "Agent" in text and ("thinking" in text or "Task output" in text):
            # Add to the thinking output
            self.thinking_output += text
            
            # Update the Streamlit display
            self.st_container.text_area(
                "Agent Thinking Process", 
                self.thinking_output, 
                height=400
            )
        
    def flush(self):
        self.stdout.flush()

def main():
    st.set_page_config(
        page_title="Guardian Evaluation System",
        page_icon="🛡️",
        layout="wide"
    )
    
    st.title("🛡️ Guardian Evaluation System")
    st.write("Input transaction details and view the guardian evaluation process and results")
    
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
            
            # Placeholders for agent thinking and results
            thinking_placeholder = st.empty()
            result_placeholder = st.empty()
            
            try:
                # Create a tab layout for thinking process and results
                tab1, tab2 = st.tabs(["Thinking Process", "Results"])
                
                with tab1:
                    thinking_container = st.container()
                    
                    # Capture stdout to display the thinking process
                    with StreamCapture(thinking_container) as capture:
                        # Initialize the crew
                        logger.info("Initializing the crew...")
                        crew = TamoJunto().crew()
                        
                        # Set up verbose mode to see thinking process
                        logger.info("Starting Guardian Evaluation...")
                        
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