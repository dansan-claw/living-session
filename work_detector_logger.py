#!/usr/bin/env python3
"""
Living Session - Work Detector with Full Logging

Logs all Trello interactions for debugging.
"""

import os
import json
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

from session_state import SessionState
from trello_client import TrelloClient, TrelloWorkManager, TrelloCard
from living_session import LivingSession

# Setup logging
ACTION_LOG = Path.home() / '.openclaw' / 'workspace' / '.living-sessions' / 'agent_actions.log'

def log_action(action_type, message, data=None, error=None):
    """Log an action with full details."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    entry = {
        'timestamp': timestamp,
        'type': action_type,
        'message': message,
        'data': data,
        'error': str(error) if error else None
    }
    
    # Write to log
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTION_LOG, 'a') as f:
        f.write(json.dumps(entry, default=str) + '\n')
    
    # Print
    print(f"[{action_type}] {message}")
    if error:
        print(f"  ERROR: {error}")


class LoggingWorkDetector:
    """Work detector with comprehensive logging."""
    
    def __init__(self, project_name: str, trello_board_id: str, 
                 trello_api_key: str = None, trello_token: str = None):
        self.project_name = project_name
        self.trello_board_id = trello_board_id
        
        log_action('INIT', f'Initializing work detector for {project_name}')
        
        # Initialize Trello client
        try:
            self.trello_client = TrelloClient(trello_api_key, trello_token)
            log_action('TRELLO', 'TrelloClient initialized successfully')
        except Exception as e:
            log_action('TRELLO', 'Failed to initialize TrelloClient', error=e)
            raise
            
        self.work_manager = TrelloWorkManager(self.trello_client, trello_board_id)
        self.state_mgr = SessionState(project_name)
        self.current_card: Optional[TrelloCard] = None
        
    def detect_work(self) -> bool:
        """Detect work with full logging."""
        log_action('DETECT', 'Starting work detection')
        
        # Check for blocked items
        log_action('TRELLO', 'Fetching blocked work items...')
        try:
            blocked = self.work_manager.get_blocked_work()
            log_action('TRELLO', f'Found {len(blocked)} blocked items', 
                      data=[c.name for c in blocked])
        except Exception as e:
            log_action('TRELLO', 'Error fetching blocked items', error=e)
            blocked = []
        
        # Check for current work
        log_action('TRELLO', 'Checking In Progress list...')
        try:
            current = self.work_manager.get_current_work()
            if current:
                log_action('WORK', f'Continuing current work: {current.name}',
                          data={'card_id': current.id, 'list': 'In Progress'})
                self.current_card = current
                self._update_state_with_work(current)
                return True
            else:
                log_action('WORK', 'No work currently in progress')
        except Exception as e:
            log_action('TRELLO', 'Error checking current work', error=e)
        
        # Check for ready work
        log_action('TRELLO', 'Checking Backlog for ready work...')
        try:
            ready = self.work_manager.get_ready_work()
            log_action('TRELLO', f'Found {len(ready)} ready items in Backlog',
                      data=[c.name for c in ready])
            
            if ready:
                next_work = ready[0]
                log_action('WORK', f'Starting new work: {next_work.name}',
                          data={'card_id': next_work.id})
                
                # Move to In Progress
                log_action('TRELLO', f'Moving card to In Progress: {next_work.name}')
                try:
                    if self.work_manager.start_work(next_work):
                        log_action('TRELLO', 'Successfully moved to In Progress')
                        self.current_card = next_work
                        self._update_state_with_work(next_work)
                        
                        # Add comment
                        log_action('TRELLO', 'Adding start comment...')
                        self.work_manager.add_progress_comment(
                            next_work,
                            f"🚀 Living session started work\nProject: {self.project_name}\nTime: {datetime.now().isoformat()}"
                        )
                        log_action('TRELLO', 'Comment added')
                        return True
                    else:
                        log_action('TRELLO', 'Failed to move to In Progress')
                except Exception as e:
                    log_action('TRELLO', 'Error moving card', error=e)
            else:
                log_action('WORK', 'No ready work found in Backlog')
        except Exception as e:
            log_action('TRELLO', 'Error fetching ready work', error=e)
        
        log_action('DETECT', 'No work available')
        return False
        
    def do_work_cycle(self) -> bool:
        """Perform work cycle with logging."""
        log_action('CYCLE', 'Starting work cycle')
        
        if not self.detect_work():
            log_action('CYCLE', 'No work detected, ending cycle')
            return False
            
        log_action('WORK', f'Working on: {self.current_card.name}')
        
        # Simulate work
        log_action('WORK', 'Executing work...')
        
        # Add progress comment
        try:
            log_action('TRELLO', 'Adding progress comment...')
            self.work_manager.add_progress_comment(
                self.current_card,
                f"✅ Work cycle completed\nTime: {datetime.now().isoformat()}"
            )
            log_action('TRELLO', 'Progress comment added')
        except Exception as e:
            log_action('TRELLO', 'Error adding comment', error=e)
        
        # Complete work
        try:
            log_action('TRELLO', f'Moving to Done: {self.current_card.name}')
            if self.work_manager.complete_work(self.current_card):
                log_action('TRELLO', 'Successfully moved to Done')
            else:
                log_action('TRELLO', 'Failed to move to Done')
        except Exception as e:
            log_action('TRELLO', 'Error completing work', error=e)
        
        # Clear current work
        self.current_card = None
        self._clear_work_from_state()
        
        log_action('CYCLE', 'Work cycle complete')
        return True
        
    def _update_state_with_work(self, card: TrelloCard) -> None:
        """Update session state."""
        state = self.state_mgr.load() or {}
        state['current_card'] = card.id
        state['current_card_name'] = card.name
        state['last_action'] = datetime.now().isoformat()
        state['status'] = 'working'
        self.state_mgr.save(state)
        log_action('STATE', 'Session state updated', 
                  data={'card': card.name, 'status': 'working'})
        
    def _clear_work_from_state(self) -> None:
        """Clear work from state."""
        state = self.state_mgr.load() or {}
        state['current_card'] = None
        state['current_card_name'] = None
        state['last_action'] = datetime.now().isoformat()
        state['status'] = 'idle'
        self.state_mgr.save(state)
        log_action('STATE', 'Session state cleared', data={'status': 'idle'})
        
    def get_work_callback(self) -> Callable:
        """Return the work callback."""
        return self.do_work_cycle


def create_logging_detector(project_name: str, config: dict):
    """Factory function to create a logging work detector."""
    return LoggingWorkDetector(
        project_name=project_name,
        trello_board_id=config.get('trello_board_id'),
        trello_api_key=config.get('trello_api_key') or os.environ.get('TRELLO_API_KEY'),
        trello_token=config.get('trello_token') or os.environ.get('TRELLO_TOKEN')
    )


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: work_detector_logger.py <project_name>")
        sys.exit(1)
        
    project = sys.argv[1]
    
    # Load config
    from config_manager import ConfigManager
    manager = ConfigManager()
    config_obj = manager.get_project_config(project)
    
    if not config_obj:
        print(f"No config for {project}")
        sys.exit(1)
        
    # Create detector and run
    detector = create_logging_detector(project, config_obj.to_dict())
    result = detector.do_work_cycle()
    
    print(f"\nWork cycle result: {result}")
    print(f"Log file: {ACTION_LOG}")
