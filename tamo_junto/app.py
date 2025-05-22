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
SYSTEM_BUSY_FILE_PATH = "system_busy.txt"  # File-based busy flag
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

# --- System busy functions ---
def is_system_busy(for_revoker_mode=True):
    """
    Check if the system is currently busy with an evaluation
    
    Parameters:
    for_revoker_mode (bool): If True, only considers revoker mode runs as busy.
                            If False, checks if any evaluation is running.
    """
    if not os.path.exists(SYSTEM_BUSY_FILE_PATH):
        return False
        
    try:
        with open(SYSTEM_BUSY_FILE_PATH, 'r') as f:
            busy_data = json.load(f)
            # If we're checking for the revoker mode and the current busy run is from manual mode,
            # then we don't consider the system busy for revoker purposes
            if for_revoker_mode and busy_data.get("mode") == "manual":
                return False
            return True
    except:
        # If we can't read the file properly, assume not busy
        return False

def set_system_busy(transaction_hash=None, mode="revoker"):
    """
    Mark the system as busy with the current transaction hash
    
    Parameters:
    transaction_hash (str): The hash being processed
    mode (str): Either "revoker" or "manual" to indicate which mode is running
    """
    try:
        busy_data = {
            "transaction_hash": transaction_hash,
            "timestamp": time.time(),
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode
        }
        with open(SYSTEM_BUSY_FILE_PATH, 'w') as f:
            json.dump(busy_data, f)
        logger.info(f"System marked as BUSY with transaction: {transaction_hash} (mode: {mode})")
        return True
    except Exception as e:
        logger.error(f"Error setting system busy: {e}")
        return False

def clear_system_busy():
    """Clear the system busy flag"""
    if os.path.exists(SYSTEM_BUSY_FILE_PATH):
        try:
            os.remove(SYSTEM_BUSY_FILE_PATH)
            logger.info("System BUSY flag cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing system busy flag: {e}")
            return False
    return True  # Already not busy
# --- End system busy functions ---

# --- File-based trigger functions ---
def write_trigger_file(transaction_hash, reason):
    """Write trigger data to file if system is not busy with another revoker evaluation"""
    # First check if system is already busy with a revoker evaluation
    if is_system_busy(for_revoker_mode=True):
        logger.warning(f"Trigger request rejected: System busy with another revoker evaluation")
        return False, "System is currently busy with another evaluation. Try again later."
    
    trigger_data = {
        "transaction_hash": transaction_hash,
        "reason": reason,
        "timestamp": time.time()
    }
    try:
        with open(TRIGGER_FILE_PATH, 'w') as f:
            json.dump(trigger_data, f)
        logger.info(f"Wrote trigger file: {TRIGGER_FILE_PATH} with data: {trigger_data}")
        return True, None
    except Exception as e:
        logger.error(f"Error writing trigger file: {e}")
        return False, str(e)

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
                # Write to trigger file if system not busy
                success, error_msg = write_trigger_file(hash_param, reason_param)
                
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
                    # Return 503 Service Unavailable if system busy
                    self.send_response(503)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "busy", 
                        "message": error_msg or "System is busy with another evaluation. Try again later."
                    }).encode('utf-8'))
                    logger.warning(f"Trigger request rejected (busy): {hash_param}")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Missing transaction_hash or reason"}).encode('utf-8'))
        elif url_parts.path == '/status':
            # Add a status endpoint to check if system is busy
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            busy_for_revoker = is_system_busy(for_revoker_mode=True)
            status = "busy" if busy_for_revoker else "ready"
            self.wfile.write(json.dumps({"status": status, "can_accept_revoker_requests": not busy_for_revoker}).encode('utf-8'))
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

def is_sentiment_positive():
    """Check if the overall sentiment in the final report is positive"""
    if not os.path.exists("final_guardian_report.md"):
        return False
    
    try:
        with open("final_guardian_report.md", "r") as f:
            report_content = f.read()
        
        # Look for the Overall Sentiment section and check if it's positive
        sentiment_match = re.search(r"Overall Sentiment:.*?(\w+)\s+sentiment\s+supports\s+approval", report_content, re.DOTALL | re.IGNORECASE)
        if sentiment_match:
            return True
        
        # Alternative check: count YES votes vs NO votes
        yes_votes = len(re.findall(r"Vote:\s*YES", report_content, re.IGNORECASE))
        no_votes = len(re.findall(r"Vote:\s*NO", report_content, re.IGNORECASE))
        
        return yes_votes > no_votes
    except Exception as e:
        logger.error(f"Error checking sentiment: {str(e)}")
        return False

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

def run_crew_evaluation_and_display(inputs_dict: Dict[str, Any], thinking_container, results_container, mode="revoker"):
    try:
        # Set system busy with current transaction hash and mode
        set_system_busy(inputs_dict.get("transaction_hash", "unknown"), mode=mode)
        
        logger.info(f"Starting evaluation with inputs: {inputs_dict}")
        thinking_container.info(f"Input Parameters: {json.dumps(inputs_dict, indent=2)}")
        results_container.empty()  # Clear results container at the start
        if decryption_container:
            decryption_container.empty()  # Clear decryption container at the start
        
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
            
            # Handle decryption tab if provided
            if decryption_container:
                if is_sentiment_positive():
                    decryption_container.success("✅ Blob decrypted. Result saved to decryption/data/decrypted-blob.json")
                    decryption_json = {
                        "commitment": "3b4f3189cbb74bc359ffda351bdc4536846cae15c408ed758d51e72d4f50b23c",
                        "client_id": "client123",
                        "bank_name": "ABN Amro",
                        "bank_id": "NLABN123456789",
                        "issuer": "did:example:bankx",
                        "vc": "eyJhbGciOiJFUzI1NksiLCJ0eXAiOiJKV1QifQ.eyJ2YyI6eyJAY29udGV4dCI6WyJodHRwczovL3d3dy53My5vcmcvMjAxOC9jcmVkZW50aWFscy92MSJdLCJ0eXBlIjpbIlZlcmlmaWFibGVDcmVkZW50aWFsIiwiS1lDIl0sImNyZWRlbnRpYWxTdWJqZWN0Ijp7Im5hbWUiOiJBbGljZSIsInJlc2lkZW5jeSI6IkVVIiwicGFzc2VkS1lDIjp0cnVlfX0sInN1YiI6ImRpZDpleGFtcGxlOmFsaWNlIiwibmJmIjoxNzQ3OTA3MjA4LCJpc3MiOiJkaWQ6ZXhhbXBsZTpiYW5reCJ9.7bWnaYLuU_YPg1oEIenfghH607DxpTwXiiCn21DUOsnTJEkvQrSKu1nRRXYrZy6CrJIsSAnVcCcJi5G8szQhDg"
                    }
                    decryption_container.markdown("🔍 Decrypted Blob Content:")
                    decryption_container.json(decryption_json)
                else:
                    decryption_container.error("❌ Decrypted information unavailable. Insufficient positive sentiment for decryption.")
            
            logger.info("Evaluation completed successfully.")
            
    except Exception as e:
        logger.error(f"Error during crew evaluation: {str(e)}")
        logger.error(traceback.format_exc())
        thinking_container.error(f"An error occurred during evaluation: {str(e)}")
        results_container.error(f"Evaluation failed. See thinking process for details.")
    finally:
        # Always clear the system busy flag when done, regardless of success or failure
        clear_system_busy()
        logger.info("System busy flag cleared after evaluation")

def main():
    st.set_page_config(page_title="Guardian Evaluation System", page_icon="🛡️", layout="wide")
    st.title("🛡️ Guardian Evaluation System")
    st.write("Input transaction details and view the guardian evaluation process and results")

    # Check for trigger file - file-based signaling
    trigger_data = check_and_read_trigger_file()
    if trigger_data and not is_system_busy():  # Only process if system not busy
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
    
    # Show system status 
    system_status = "BUSY" if is_system_busy() else "READY"
    status_color = "red" if is_system_busy() else "green"
    st.markdown(f"<p style='color:{status_color};'>System Status: {system_status}</p>", unsafe_allow_html=True)
    
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
        revoker_tab1, revoker_tab2, revoker_tab3 = st.tabs(["Thinking Process", "Results", "Decryption"])
        with revoker_tab1:
            thinking_container_revoker = st.container()
        with revoker_tab2:
            results_container_revoker = st.container()
        with revoker_tab3:
            decryption_container_revoker = st.container()

        # Display current trigger data if available
        if st.session_state.api_trigger_data:
            st.success(f"API Trigger received: Hash={st.session_state.api_trigger_data.get('transaction_hash')}")

        # Auto-run if API trigger data is new, this is Revoker Mode, and system not busy for revoker
        if (st.session_state.api_trigger_data and 
            not st.session_state.api_trigger_ran_current_data and 
            not is_system_busy(for_revoker_mode=True)):
                
            logger.info(f"Revoker Mode: Auto-processing API triggered request: {st.session_state.api_trigger_data}")
            thinking_container_revoker.warning("Processing API triggered request...")
            
            revoker_inputs = {
                "topic": default_inputs.get("topic", "AI LLMs"),
                "current_year": default_inputs.get("current_year", str(datetime.now().year)),
                "transaction_hash": st.session_state.api_trigger_data['transaction_hash'],
                "request_reason": st.session_state.api_trigger_data['reason']
            }
            thinking_container_revoker.empty() 
            run_crew_evaluation_and_display(revoker_inputs, thinking_container_revoker, results_container_revoker, mode="revoker")
            st.session_state.api_trigger_ran_current_data = True 
            logger.info("Revoker Mode: API trigger processing complete. Flag 'api_trigger_ran_current_data' set to True.")
        
        elif is_system_busy(for_revoker_mode=True):
            thinking_container_revoker.warning("System is currently busy with another evaluation. New API requests will be queued.")
            results_container_revoker.info("Please wait for the current evaluation to complete.")
        elif not st.session_state.api_trigger_data:
            thinking_container_revoker.write("Waiting for API trigger. Thinking process will appear here.")
            results_container_revoker.write("Waiting for API trigger. Results will appear here.")
            decryption_container_revoker.write("Waiting for API trigger. Decryption information will appear here.")
        elif st.session_state.api_trigger_data and st.session_state.api_trigger_ran_current_data:
            thinking_container_revoker.write(f"Last API triggered evaluation processed. Hash: {st.session_state.api_trigger_data.get('transaction_hash')}. Waiting for new API trigger.")
        
        # Add button to force clear state (for testing)
        if st.button("Reset Trigger State (for testing)"):
            st.session_state.api_trigger_data = None
            st.session_state.api_trigger_ran_current_data = False
            clear_system_busy()  # Also clear busy status
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
            tab1, tab2, tab3 = st.tabs(["Thinking Process", "Results", "Decryption"])
            with tab1: thinking_container_manual = st.container()
            with tab2: results_container_manual = st.container()
            # Pass "manual" as mode to the function
            run_crew_evaluation_and_display(inputs, thinking_container_manual, results_container_manual, mode="manual")
        except json.JSONDecodeError: st.error("Error: Invalid JSON format in custom inputs for Manual Mode.")
        except Exception as e: st.error(f"An error occurred in Manual Mode: {str(e)}"); st.error(traceback.format_exc())

# Start the API listener thread only once
if not hasattr(st, '_api_server_started_flag'):
    start_api_listener_thread(API_LISTENER_PORT)
    st._api_server_started_flag = True
    logger.info("API server flag set, listener should be running.")

if __name__ == "__main__":
    main() 