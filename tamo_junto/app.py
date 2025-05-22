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

import threading
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import time  # For timestamp in trigger file

# Load environment variables from .env file
load_dotenv()

# --- Global variables for API trigger ---
API_LISTENER_PORT = 8502
TRIGGER_FILE_PATH = "revoker_trigger.json"  # File-based signaling
# --- End Global variables ---

# Import from the installed tamo_junto package
from tamo_junto.crew import TamoJunto
from tamo_junto.config.inputs import get_default_inputs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('guardian_evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if os.environ.get("OPENAI_API_KEY"):
    logger.info("OPENAI_API_KEY is set in environment")
else:
    logger.warning("OPENAI_API_KEY is not set in environment")

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# --- File-based trigger functions ---
def write_trigger_file(transaction_hash, reason):
    """Write trigger data to file"""
    trigger_data = {
        "transaction_hash": transaction_hash,
        "reason": reason,
        "timestamp": time.time()
    }
    try:
        with open(TRIGGER_FILE_PATH, 'w') as f:
            json.dump(trigger_data, f)
        logger.info(f"Wrote trigger file: {TRIGGER_FILE_PATH} with data: {trigger_data}")
        return True
    except Exception as e:
        logger.error(f"Error writing trigger file: {e}")
        return False

def check_and_read_trigger_file():
    """Read and process trigger file if it exists"""
    if not os.path.exists(TRIGGER_FILE_PATH):
        return None
    
    try:
        with open(TRIGGER_FILE_PATH, 'r') as f:
            trigger_data = json.load(f)
        
        # Remove the file after reading
        os.remove(TRIGGER_FILE_PATH)
        logger.info(f"Processed trigger file with data: {trigger_data}")
        return trigger_data
    except Exception as e:
        logger.error(f"Error reading trigger file: {e}")
        try:
            # Clean up the file if it exists but is corrupted
            if os.path.exists(TRIGGER_FILE_PATH):
                os.remove(TRIGGER_FILE_PATH)
        except:
            pass
        return None
# --- End file-based trigger functions ---

# --- HTTP Server for API Trigger ---
class TriggerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        url_parts = urlparse(self.path)
        if url_parts.path == '/trigger_revoker':
            query_params = parse_qs(url_parts.query)
            hash_param = query_params.get('transaction_hash', [None])[0]
            reason_param = query_params.get('reason', [None])[0]

            if hash_param and reason_param:
                # Write to trigger file instead of using in-memory variables
                success = write_trigger_file(hash_param, reason_param)
                
                if success:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        "status": "success", 
                        "message": "Revoker triggered", 
                        "data": {"transaction_hash": hash_param, "reason": reason_param}
                    }
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    logger.info(f"Trigger request successful: {hash_param}, {reason_param}")
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Failed to create trigger file"}).encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Missing transaction_hash or reason"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not Found")

def start_api_listener_thread(port: int):
    def run_server():
        with socketserver.TCPServer(("", port), TriggerHandler) as httpd:
            logger.info(f"API listener started on http://localhost:{port}/trigger_revoker")
            httpd.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info(f"API listener thread initiated for port {port}.")

# --- End HTTP Server ---

def extract_summary(result):
    if hasattr(result, "__str__"):
        result_text = str(result)
    else:
        result_text = result
    logger.info(f"Result type: {type(result)}")
    sample = result_text[:100] + "..." if len(result_text) > 100 else result_text
    logger.info(f"Result sample: {sample}")
    final_answers = re.findall(r'Final Answer:.*?(YES|NO|ABSTAIN)\.?\s+(.*?)(?=\n\n|\Z)', result_text, re.DOTALL)
    if final_answers:
        summary = "Summary of Guardian Evaluations:\n\n"
        for decision, justification in final_answers:
            short_justification = justification.strip()
            if len(short_justification) > 200:
                short_justification = short_justification[:197] + "..."
            summary += f"- Decision: {decision}\n  Justification: {short_justification}\n\n"
        return summary
    return result_text

class StreamCapture:
    def __init__(self, st_container):
        self.st_container = st_container
        self.buffer = io.StringIO()
        self.stdout = sys.stdout
        self.output_text = ""
        self.auto_update = True
        self.output_placeholder = st_container.empty()
        self.update_placeholder = st_container.empty()
        
    def __enter__(self):
        sys.stdout = self
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.stdout
        
    def strip_ansi(self, text):
        return ANSI_ESCAPE.sub('', text)
        
    def write(self, text):
        self.buffer.write(text)
        clean_text = self.strip_ansi(text)
        self.output_text += clean_text
        if self.auto_update:
            self.output_placeholder.code(self.output_text, language="")
            if any(marker in clean_text for marker in ["Agent:", "Task Completion", "Final Answer"]):
                lines = self.output_text.splitlines()
                last_lines = lines[-min(10, len(lines)):]
                important_text = "\n".join(last_lines)
                self.update_placeholder.markdown("### Important Update")
                self.update_placeholder.code(important_text, language="")
        
    def flush(self):
        self.stdout.flush()
        
    def toggle_updates(self):
        self.auto_update = not self.auto_update
        return self.auto_update

def run_crew_evaluation_and_display(inputs_dict: Dict[str, Any], thinking_container, results_container):
    try:
        logger.info(f"Starting evaluation with inputs: {inputs_dict}")
        thinking_container.info(f"Input Parameters: {json.dumps(inputs_dict, indent=2)}")
        results_container.empty()  # Clear results container at the start
        
        with StreamCapture(thinking_container) as capture:
            logger.info("Initializing the crew...")
            crew = TamoJunto().crew()
            logger.info("Starting Guardian Evaluation...")
            result = crew.kickoff(inputs=inputs_dict)
            logger.info(f"Received result of type: {type(result)}")
            summary = ""
            try:
                summary = extract_summary(result)
                logger.info("Successfully extracted summary")
            except Exception as summary_error:
                logger.error(f"Error extracting summary: {str(summary_error)}")
                summary = f"Error extracting summary. Raw result type: {type(result)}. Raw result: {str(result)[:500]}..."
            results_container.write("### Guardian Evaluation Result")
            results_container.markdown(summary)
            if os.path.exists("final_guardian_report.md"):
                with open("final_guardian_report.md", "r") as f:
                    report_content = f.read()
                results_container.write("### Final Guardian Report")
                results_container.markdown(report_content)
            logger.info("Evaluation completed successfully.")
    except Exception as e:
        logger.error(f"Error during crew evaluation: {str(e)}")
        logger.error(traceback.format_exc())
        thinking_container.error(f"An error occurred during evaluation: {str(e)}")
        results_container.error(f"Evaluation failed. See thinking process for details.")

def main():
    st.set_page_config(page_title="Guardian Evaluation System", page_icon="🛡️", layout="wide")
    st.title("🛡️ Guardian Evaluation System")
    st.write("Input transaction details and view the guardian evaluation process and results")

    # Check for trigger file - file-based signaling
    trigger_data = check_and_read_trigger_file()
    if trigger_data:
        logger.info(f"Found trigger file with data: {trigger_data}")
        if 'api_trigger_data' not in st.session_state:
            st.session_state.api_trigger_data = {}
        
        st.session_state.api_trigger_data = {
            "transaction_hash": trigger_data["transaction_hash"],
            "reason": trigger_data["reason"]
        }
        if 'api_trigger_ran_current_data' not in st.session_state:
            st.session_state.api_trigger_ran_current_data = False
        else:
            st.session_state.api_trigger_ran_current_data = False  # Reset to false to process new trigger
        
        # Force switch to Revoker Mode if not already there
        st.session_state.mode_select = 'Revoker Mode'
        logger.info("API trigger detected. Session state updated. Forcing Revoker Mode.")
        st.rerun()  # Force rerun to update UI and process new API data
    
    # Initialize session state variables if not present
    if 'api_trigger_data' not in st.session_state:
        st.session_state.api_trigger_data = None
    if 'api_trigger_ran_current_data' not in st.session_state:
        st.session_state.api_trigger_ran_current_data = False

    mode = st.radio("Select Mode:", ('Manual Input', 'Revoker Mode'), key="mode_select")
    
    if not os.environ.get("OPENAI_API_KEY"):
        st.error("❌ OpenAI API key is not configured. Please check your .env file.")
        st.info("Create a .env file in the tamo_junto directory with the content: OPENAI_API_KEY=your_api_key_here")
        return
    
    default_inputs = get_default_inputs()
    submit_button = False

    if mode == 'Manual Input':
        st.session_state.api_trigger_data = None # Clear API trigger if switching to manual
        st.session_state.api_trigger_ran_current_data = False

        with st.form(key="input_form"):
            col1, col2 = st.columns(2)
            with col1:
                topic = st.text_input("Topic", value=default_inputs.get("topic", ""))
                transaction_hash = st.text_input("Transaction Hash", value=default_inputs.get("transaction_hash", ""))
            with col2:
                current_year = st.text_input("Current Year", value=default_inputs.get("current_year", str(datetime.now().year)))
                request_reason = st.text_area("Request Reason", value=default_inputs.get("request_reason", ""))
            st.subheader("Additional Custom Inputs (JSON Format)")
            custom_inputs_str = st.text_area("Custom Inputs (JSON)", value="{}", height=150)
            submit_button = st.form_submit_button(label="Evaluate Transaction")
    
    elif mode == 'Revoker Mode':
        st.info("Revoker Mode: Waiting for API trigger to process a request.")
        
        # Create containers for output upfront
        revoker_tab1, revoker_tab2 = st.tabs(["Thinking Process", "Results"])
        with revoker_tab1:
            thinking_container_revoker = st.container()
        with revoker_tab2:
            results_container_revoker = st.container()

        # Display current trigger data if available
        if st.session_state.api_trigger_data:
            st.success(f"API Trigger received: Hash={st.session_state.api_trigger_data.get('transaction_hash')}")

        # Auto-run if API trigger data is new and this is Revoker Mode
        if st.session_state.api_trigger_data and not st.session_state.api_trigger_ran_current_data:
            logger.info(f"Revoker Mode: Auto-processing API triggered request: {st.session_state.api_trigger_data}")
            thinking_container_revoker.warning("Processing API triggered request...")
            
            revoker_inputs = {
                "topic": default_inputs.get("topic", "AI LLMs"),
                "current_year": default_inputs.get("current_year", str(datetime.now().year)),
                "transaction_hash": st.session_state.api_trigger_data['transaction_hash'],
                "request_reason": st.session_state.api_trigger_data['reason']
            }
            thinking_container_revoker.empty() 
            run_crew_evaluation_and_display(revoker_inputs, thinking_container_revoker, results_container_revoker)
            st.session_state.api_trigger_ran_current_data = True 
            logger.info("Revoker Mode: API trigger processing complete. Flag 'api_trigger_ran_current_data' set to True.")
        
        elif not st.session_state.api_trigger_data:
            thinking_container_revoker.write("Waiting for API trigger. Thinking process will appear here.")
            results_container_revoker.write("Waiting for API trigger. Results will appear here.")
        elif st.session_state.api_trigger_data and st.session_state.api_trigger_ran_current_data:
            thinking_container_revoker.write(f"Last API triggered evaluation processed. Hash: {st.session_state.api_trigger_data.get('transaction_hash')}. Waiting for new API trigger.")
        
        # Add button to force clear state (for testing)
        if st.button("Reset Trigger State (for testing)"):
            st.session_state.api_trigger_data = None
            st.session_state.api_trigger_ran_current_data = False
            if os.path.exists(TRIGGER_FILE_PATH):
                os.remove(TRIGGER_FILE_PATH)
            st.rerun()

    if submit_button and mode == 'Manual Input':
        try:
            custom_inputs = json.loads(custom_inputs_str)
            inputs = {
                "topic": topic, "current_year": current_year,
                "transaction_hash": transaction_hash, "request_reason": request_reason,
                **custom_inputs
            }
            st.write("### Input Parameters (Manual Mode)")
            st.json(inputs)
            tab1, tab2 = st.tabs(["Thinking Process", "Results"])
            with tab1: thinking_container_manual = st.container()
            with tab2: results_container_manual = st.container()
            run_crew_evaluation_and_display(inputs, thinking_container_manual, results_container_manual)
        except json.JSONDecodeError: st.error("Error: Invalid JSON format in custom inputs for Manual Mode.")
        except Exception as e: st.error(f"An error occurred in Manual Mode: {str(e)}"); st.error(traceback.format_exc())

# Start the API listener thread only once
if not hasattr(st, '_api_server_started_flag'):
    start_api_listener_thread(API_LISTENER_PORT)
    st._api_server_started_flag = True
    logger.info("API server flag set, listener should be running.")

if __name__ == "__main__":
    main() 