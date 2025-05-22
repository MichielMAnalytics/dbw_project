from datetime import datetime
from typing import Dict, Any

def get_default_inputs() -> Dict[str, Any]:
    """Get default inputs for the crew."""
    return {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year),
        'transaction_hash': '0x9491a40dab86447b8b97505c3dabcf61',
        'request_reason': 'Suspicious transaction pattern detected'
    }