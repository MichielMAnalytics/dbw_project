# api.py (separate from your Streamlit app)
from fastapi import FastAPI, Query
import uvicorn
import logging
import sys
import os
import re
from dotenv import load_dotenv
import traceback

# Load environment variables from .env file
load_dotenv()

# Import from the installed tamo_junto package
from tamo_junto.crew import TamoJunto
from tamo_junto.config.inputs import get_default_inputs

# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('guardian_api.log'),
        logging.StreamHandler(sys.stdout)  # This ensures logs go to stdout
    ]
)

logger = logging.getLogger(__name__)

# Log the API key status (don't log the actual key!)
if os.environ.get("OPENAI_API_KEY"):
    logger.info("OPENAI_API_KEY is set in environment")
else:
    logger.warning("OPENAI_API_KEY is not set in environment")

app = FastAPI(title="Guardian Evaluation API")

def extract_summary(result):
    """
    Extract a summary from the full evaluation result.
    
    This function handles a CrewOutput object or string and extracts key information.
    """
    # Convert CrewOutput to string if needed
    if hasattr(result, "__str__"):
        result_text = str(result)
    else:
        # If it's already a string
        result_text = result
    
    # Log the result type and a sample for debugging
    logger.info(f"Result type: {type(result)}")
    sample = result_text[:100] + "..." if len(result_text) > 100 else result_text
    logger.info(f"Result sample: {sample}")
    
    # Extract Final Answer sections
    final_answers = re.findall(r'Final Answer:.*?(YES|NO|ABSTAIN)\.?\s+(.*?)(?=\n\n|\Z)', result_text, re.DOTALL)
    
    if final_answers:
        # Construct summary from all Final Answers
        summary = "Summary of Guardian Evaluations:\n\n"
        for decision, justification in final_answers:
            # Clean up and shorten the justification
            short_justification = justification.strip()
            if len(short_justification) > 200:
                short_justification = short_justification[:197] + "..."
            
            summary += f"- Decision: {decision}\n  Justification: {short_justification}\n\n"
        
        return summary
    
    # Fallback if no Final Answer sections found
    # Return a shortened version of the result
    return result_text

@app.get("/")
async def root():
    return {"message": "Guardian Evaluation API is running. Use /evaluate endpoint."}

@app.get("/evaluate", response_model=None)
async def evaluate_transaction(
    transaction_hash: str = Query(..., description="Transaction hash to evaluate"),
    reason: str = Query(..., description="Reason for the evaluation request"),
    topic: str = Query(None, description="Optional topic"),
    year: str = Query(None, description="Current year (optional)")
):
    try:
        logger.info(f"Starting evaluation for transaction: {transaction_hash}")
        
        # Get default inputs and override with provided values
        inputs = get_default_inputs()
        
        # Update with provided values
        inputs["transaction_hash"] = transaction_hash
        inputs["request_reason"] = reason
        
        if topic:
            inputs["topic"] = topic
        if year:
            inputs["current_year"] = year
            
        logger.info(f"Inputs prepared: {inputs}")
        
        # Initialize the crew
        crew = TamoJunto().crew()
        
        # Run the crew with the inputs
        logger.info("Starting Guardian Evaluation...")
        result = crew.kickoff(inputs=inputs)
        
        # Log the result type
        logger.info(f"Received result of type: {type(result)}")
        
        # Extract summary from the full result
        try:
            summary = extract_summary(result)
            logger.info("Successfully extracted summary")
        except Exception as summary_error:
            logger.error(f"Error extracting summary: {str(summary_error)}")
            summary = f"Error extracting summary. Raw result type: {type(result)}"
        
        logger.info("Evaluation completed successfully")
        
        # Return only the summary as plain text
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(summary)
        
    except Exception as e:
        logger.error(f"Error during evaluation: {str(e)}")
        logger.error(traceback.format_exc())
        # Return error as plain text
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(f"Error: {str(e)}", status_code=500)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)