#!/usr/bin/env python3
"""
Living Session - Work Detector with 5-Minute Work Cycles

Proper workflow: Backlog → In Progress → Work (5 min) → Done
"""

import os
import time
import json
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

from session_state import SessionState
from trello_client import TrelloClient, TrelloWorkManager, TrelloCard
from living_session import LivingSession

# Setup logging
ACTION_LOG = Path.home() / '.openclaw' / 'workspace' / '.living-sessions' / 'agent_actions.log'
WORK_CYCLE_MINUTES = 5  # Configurable work cycle time

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
    
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTION_LOG, 'a') as f:
        f.write(json.dumps(entry, default=str) + '\n')
    
    print(f"[{action_type}] {message}")
    if error:
        print(f"  ERROR: {error}")


class TimedWorkDetector:
    """Work detector with proper 5-minute work cycles."""
    
    def __init__(self, project_name: str, trello_board_id: str, 
                 trello_api_key: str = None, trello_token: str = None):
        self.project_name = project_name
        self.trello_board_id = trello_board_id
        self.work_cycle_seconds = WORK_CYCLE_MINUTES * 60
        
        log_action('INIT', f'Initializing timed work detector for {project_name}')
        log_action('CONFIG', f'Work cycle time: {WORK_CYCLE_MINUTES} minutes ({self.work_cycle_seconds}s)')
        
        try:
            self.trello_client = TrelloClient(trello_api_key, trello_token)
            log_action('TRELLO', 'TrelloClient initialized successfully')
        except Exception as e:
            log_action('TRELLO', 'Failed to initialize TrelloClient', error=e)
            raise
            
        self.work_manager = TrelloWorkManager(self.trello_client, trello_board_id)
        self.state_mgr = SessionState(project_name)
        self.current_card: Optional[TrelloCard] = None
        
    def start_work(self, card: TrelloCard) -> bool:
        """Start working on a card - move to In Progress."""
        log_action('WORKFLOW', f'Starting work on: {card.name}')
        
        # Move to In Progress
        log_action('TRELLO', f'Moving to In Progress: {card.name}')
        try:
            if self.work_manager.start_work(card):
                log_action('TRELLO', 'Successfully moved to In Progress')
                self.current_card = card
                self._update_state_with_work(card, 'in_progress')
                
                # Add start comment
                self.work_manager.add_progress_comment(
                    card,
                    f"🚀 Work started at {datetime.now().strftime('%H:%M:%S')}\n"
                    f"Estimated duration: {WORK_CYCLE_MINUTES} minutes\n"
                    f"Project: {self.project_name}"
                )
                log_action('TRELLO', 'Start comment added')
                return True
            else:
                log_action('TRELLO', 'Failed to move to In Progress')
                return False
        except Exception as e:
            log_action('TRELLO', 'Error starting work', error=e)
            return False
    
    def do_work(self) -> bool:
        """Perform actual work for 5 minutes with progress updates."""
        if not self.current_card:
            log_action('WORK', 'No current card to work on')
            return False
        
        log_action('WORK', f'Starting {WORK_CYCLE_MINUTES}-minute work cycle')
        log_action('WORK', f'Working on: {self.current_card.name}')
        
        # Work in intervals, logging progress
        total_seconds = self.work_cycle_seconds
        update_interval = 60  # Log progress every minute
        elapsed = 0
        
        while elapsed < total_seconds:
            # Sleep for update interval
            time.sleep(min(update_interval, total_seconds - elapsed))
            elapsed += update_interval
            
            # Log progress
            progress_pct = int((elapsed / total_seconds) * 100)
            remaining = total_seconds - elapsed
            
            log_action('PROGRESS', f'{progress_pct}% complete ({elapsed}s / {total_seconds}s)')
            
            # Add progress comment every minute
            try:
                self.work_manager.add_progress_comment(
                    self.current_card,
                    f"⏳ Progress: {progress_pct}%\n"
                    f"Elapsed: {elapsed // 60}m {elapsed % 60}s\n"
                    f"Remaining: ~{remaining // 60}m"
                )
                log_action('TRELLO', f'Progress comment added: {progress_pct}%')
            except Exception as e:
                log_action('TRELLO', 'Error adding progress comment', error=e)
        
        log_action('WORK', f'Work cycle complete after {WORK_CYCLE_MINUTES} minutes')
        return True
    
    def complete_work(self) -> bool:
        """Complete work and move card to Done."""
        if not self.current_card:
            log_action('WORK', 'No current card to complete')
            return False
        
        log_action('WORKFLOW', f'Completing work: {self.current_card.name}')
        
        # Add completion comment
        try:
            self.work_manager.add_progress_comment(
                self.current_card,
                f"✅ Work completed at {datetime.now().strftime('%H:%M:%S')}\n"
                f"Duration: {WORK_CYCLE_MINUTES} minutes\n"
                f"Status: Ready for review"
            )
            log_action('TRELLO', 'Completion comment added')
        except Exception as e:
            log_action('TRELLO', 'Error adding completion comment', error=e)
        
        # Move to Done
        log_action('TRELLO', f'Moving to Done: {self.current_card.name}')
        try:
            if self.work_manager.complete_work(self.current_card):
                log_action('TRELLO', 'Successfully moved to Done')
                self._clear_work_from_state()
                self.current_card = None
                return True
            else:
                log_action('TRELLO', 'Failed to move to Done')
                return False
        except Exception as e:
            log_action('TRELLO', 'Error completing work', error=e)
            return False
    
    def do_work_cycle(self) -> bool:
        """Complete work cycle: Start → Work (5 min) → Complete."""
        log_action('CYCLE', 'Starting complete work cycle')
        
        # Step 1: Find work
        log_action('DETECT', 'Looking for ready work in Backlog...')
        ready = self.work_manager.get_ready_work()
        
        if not ready:
            log_action('DETECT', 'No ready work found')
            return False
        
        card = ready[0]
        log_action('DETECT', f'Found work: {card.name}')
        
        # Step 2: Start work (move to In Progress)
        if not self.start_work(card):
            log_action('CYCLE', 'Failed to start work')
            return False
        
        # Step 3: Do actual work (5 minutes)
        if not self.do_work():
            log_action('CYCLE', 'Work cycle interrupted')
            return False
        
        # Step 4: Complete work (move to Done)
        if not self.complete_work():
            log_action('CYCLE', 'Failed to complete work')
            return False
        
        log_action('CYCLE', 'Work cycle completed successfully')
        return True
    
    def _update_state_with_work(self, card: TrelloCard, status: str) -> None:
        """Update session state."""
        state = self.state_mgr.load() or {}
        state['current_card'] = card.id
        state['current_card_name'] = card.name
        state['last_action'] = datetime.now().isoformat()
        state['status'] = status
        self.state_mgr.save(state)
        log_action('STATE', f'State updated: {status}', data={'card': card.name})
    
    def _clear_work_from_state(self) -> None:
        """Clear work from state."""
        state = self.state_mgr.load() or {}
        state['current_card'] = None
        state['current_card_name'] = None
        state['last_action'] = datetime.now().isoformat()
        state['status'] = 'idle'
        self.state_mgr.save(state)
        log_action('STATE', 'State cleared', data={'status': 'idle'})
    
    def get_work_callback(self) -> Callable:
        """Return the work callback."""
        return self.do_work_cycle


def create_timed_detector(project_name: str, config: dict):
    """Factory function to create a timed work detector."""
    return TimedWorkDetector(
        project_name=project_name,
        trello_board_id=config.get('trello_board_id'),
        trello_api_key=config.get('trello_api_key') or os.environ.get('TRELLO_API_KEY'),
        trello_token=config.get('trello_token') or os.environ.get('TRELLO_TOKEN')
    )


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: work_detector_timed.py <project_name>")
        sys.exit(1)
    
    project = sys.argv[1]
    
    from config_manager import ConfigManager
    manager = ConfigManager()
    config_obj = manager.get_project_config(project)
    
    if not config_obj:
        print(f"No config for {project}")
        sys.exit(1)
    
    detector = create_timed_detector(project, config_obj.to_dict())
    result = detector.do_work_cycle()
    
    print(f"\nWork cycle result: {result}")
    print(f"Duration: {WORK_CYCLE_MINUTES} minutes")
    print(f"Log file: {ACTION_LOG}")
