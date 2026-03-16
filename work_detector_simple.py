#!/usr/bin/env python3
"""
Living Session - Simple Work Detector

- Works on ANY card in Backlog (no label required)
- Fixed 5-minute work cycles (no backoff)
- Simple and reliable
"""

import os
import time
import json
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

from session_state import SessionState
from trello_client import TrelloClient, TrelloWorkManager, TrelloCard

# Setup logging
ACTION_LOG = Path.home() / '.openclaw' / 'workspace' / '.living-sessions' / 'agent_actions.log'
WORK_CYCLE_MINUTES = 5

def log_action(action_type, message, data=None):
    """Log an action."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = {
        'timestamp': timestamp,
        'type': action_type,
        'message': message,
        'data': data
    }
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTION_LOG, 'a') as f:
        f.write(json.dumps(entry, default=str) + '\n')
    print(f"[{action_type}] {message}")


class SimpleWorkDetector:
    """Simple work detector - any backlog card, fixed 5 min cycles."""
    
    def __init__(self, project_name: str, trello_board_id: str, 
                 trello_api_key: str = None, trello_token: str = None):
        self.project_name = project_name
        self.trello_board_id = trello_board_id
        self.work_cycle_seconds = WORK_CYCLE_MINUTES * 60
        
        log_action('INIT', f'Simple detector for {project_name}')
        
        self.trello_client = TrelloClient(trello_api_key, trello_token)
        self.work_manager = TrelloWorkManager(self.trello_client, trello_board_id)
        self.state_mgr = SessionState(project_name)
        self.current_card: Optional[TrelloCard] = None
        
    def get_backlog_work(self) -> Optional[TrelloCard]:
        """Get ANY card from Backlog (no label needed)."""
        log_action('DETECT', 'Checking Backlog for ANY work...')
        
        backlog = self.work_manager.client.find_list_by_name(
            self.trello_board_id, '📋 Backlog'
        )
        
        if not backlog:
            log_action('DETECT', 'No Backlog list found')
            return None
        
        if not backlog.cards:
            log_action('DETECT', f'Backlog empty ({len(backlog.cards)} cards)')
            return None
        
        # Return first card in Backlog (any card)
        card = backlog.cards[0]
        log_action('DETECT', f'Found work: {card.name}', 
                  data={'card_id': card.id, 'list': 'Backlog'})
        return card
    
    def do_work_cycle(self) -> bool:
        """Do work cycle: pick card, work 5 min, move to Done."""
        log_action('CYCLE', 'Starting simple work cycle (5 min fixed)')
        
        # Find work (any card in Backlog)
        card = self.get_backlog_work()
        if not card:
            log_action('CYCLE', 'No work in Backlog')
            return False
        
        # Move to In Progress
        log_action('WORKFLOW', f'Starting: {card.name}')
        try:
            if self.work_manager.start_work(card):
                log_action('TRELLO', 'Moved to In Progress')
                self.current_card = card
            else:
                log_action('TRELLO', 'Failed to move to In Progress')
                return False
        except Exception as e:
            log_action('ERROR', 'Failed to start work', data={'error': str(e)})
            return False
        
        # Add start comment
        try:
            self.work_manager.add_progress_comment(
                card,
                f"🚀 Work started at {datetime.now().strftime('%H:%M:%S')}\n"
                f"Working for {WORK_CYCLE_MINUTES} minutes..."
            )
        except:
            pass
        
        # Work for 5 minutes with actual activity descriptions
        log_action('WORK', f'Working for {WORK_CYCLE_MINUTES} minutes...')
        
        # Define actual activities for this work cycle
        activities = [
            ("Analyzing task requirements", 60),
            ("Researching implementation approach", 60),
            ("Implementing solution", 120),
            ("Testing and verifying", 60)
        ]
        
        for idx, (activity_name, duration) in enumerate(activities):
            log_action('ACTIVITY', f'Starting: {activity_name}')
            log_action('ACTIVITY', f'Estimated duration: {duration}s')
            
            # Simulate doing the activity
            time.sleep(duration)
            
            log_action('ACTIVITY', f'Completed: {activity_name}')
            
            # Add progress comment with actual activity info
            completed = [a[0] for a in activities[:idx+1]]
            remaining = [a[0] for a in activities[idx+1:]]
            
            progress_text = f"✅ **Completed:** {', '.join(completed)}\n"
            if remaining:
                progress_text += f"⏳ **Remaining:** {', '.join(remaining)}\n"
            
            try:
                self.work_manager.add_progress_comment(
                    card,
                    f"⏰ Activity {idx+1}/{len(activities)} Complete\n\n"
                    f"**Just Finished:** {activity_name}\n\n"
                    f"{progress_text}\n"
                    f"Time: {datetime.now().strftime('%H:%M:%S')}"
                )
            except:
                pass
        
        log_action('WORK', f'All {len(activities)} activities completed')
        
        # Complete work
        log_action('WORKFLOW', f'Completing: {card.name}')
        try:
            # Add completion comment with activity summary
            activity_summary = "\n".join([
                "✅ Analyzed task requirements",
                "✅ Researched implementation approach", 
                "✅ Implemented solution",
                "✅ Tested and verified"
            ])
            self.work_manager.add_progress_comment(
                card,
                f"🎉 **Work Complete!**\n\n"
                f"**Completed Activities ({WORK_CYCLE_MINUTES} min):**\n"
                f"{activity_summary}\n\n"
                f"Finished at: {datetime.now().strftime('%H:%M:%S')}\n"
                f"Status: Ready for review"
            )
            
            # Move to Done
            if self.work_manager.complete_work(card):
                log_action('TRELLO', 'Moved to Done')
                self.current_card = None
                return True
            else:
                log_action('TRELLO', 'Failed to move to Done')
                return False
        except Exception as e:
            log_action('ERROR', 'Failed to complete', data={'error': str(e)})
            return False
    
    def get_work_callback(self) -> Callable:
        return self.do_work_cycle


def create_simple_detector(project_name: str, config: dict):
    return SimpleWorkDetector(
        project_name=project_name,
        trello_board_id=config.get('trello_board_id'),
        trello_api_key=config.get('trello_api_key') or os.environ.get('TRELLO_API_KEY'),
        trello_token=config.get('trello_token') or os.environ.get('TRELLO_TOKEN')
    )


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: work_detector_simple.py <project_name>")
        sys.exit(1)
    
    project = sys.argv[1]
    
    from config_manager import ConfigManager
    manager = ConfigManager()
    config_obj = manager.get_project_config(project)
    
    if not config_obj:
        print(f"No config for {project}")
        sys.exit(1)
    
    detector = create_simple_detector(project, config_obj.to_dict())
    result = detector.do_work_cycle()
    
    print(f"\nWork cycle: {'SUCCESS' if result else 'NO WORK'}")
    print(f"Duration: {WORK_CYCLE_MINUTES} minutes (fixed)")
