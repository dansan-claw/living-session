"""
Trello Action Logger

Logs all Trello API interactions for debugging.
"""

import json
from datetime import datetime
from pathlib import Path

TRELLO_LOG = Path.home() / '.openclaw' / 'workspace' / '.living-sessions' / 'trello_actions.log'

def log_trello(action, details=None, error=None):
    """Log a Trello action."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    entry = {
        'timestamp': timestamp,
        'action': action,
        'details': details,
        'error': str(error) if error else None
    }
    
    # Write to log file
    TRELLO_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(TRELLO_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    # Also print
    print(f"[TRELLO] {timestamp} - {action}")
    if details:
        print(f"         Details: {details}")
    if error:
        print(f"         ERROR: {error}")
