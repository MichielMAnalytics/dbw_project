 import time
import logging
from datetime import datetime
from typing import Dict, Any
from tamo_junto.crew import TamoJunto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crew_runner.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class CrewRunner:
    def __init__(self, sleep_interval: int = 60):
        self.sleep_interval = sleep_interval
        self.crew = TamoJunto()
    
    def run_crew_once(self) -> None:
        try:
            logger.info("Starting crew execution")
            self.crew.crew().kickoff(inputs=get_default_inputs())
            logger.info("Crew execution completed successfully")
        except Exception as e:
            logger.error(f"Error during crew execution: {str(e)}", exc_info=True)