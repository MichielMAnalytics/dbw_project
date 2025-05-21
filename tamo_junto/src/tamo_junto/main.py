import sys
import warnings

from datetime import datetime

from tamo_junto.crew import TamoJunto
from tamo_junto.config.inputs import get_default_inputs

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the crew.
    """
    try:
        TamoJunto().crew().kickoff(inputs=get_default_inputs())
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")