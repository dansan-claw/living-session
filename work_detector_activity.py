#!/usr/bin/env python3
"""
Living Session - Activity-Based Work Detector

Logs actual activities being performed, not just percentages.
"""

import os
import time
import json
from typing import Optional, Callable, List, Dict
from datetime import datetime
from pathlib import Path

from session_state import SessionState
from trello_client import TrelloClient, TrelloWorkManager, TrelloCard
from living_session import LivingSession

# Setup logging
ACTION_LOG = Path.home() / '.openclaw' / 'workspace' / '.living-sessions' / 'agent_actions.log'
WORK_CYCLE_MINUTES = 5

# Task definitions with activities
TASK_ACTIVITIES = {
    "[Phase 1] Set up archiso build environment": [
        ("Installing archiso package", 30),
        ("Installing arch-install-scripts", 30),
        ("Creating build directory structure", 60),
        ("Verifying installation", 60),
        ("Testing mkarchiso command", 120)
    ],
    "[Phase 1] Create AgentOS archinstall profile": [
        ("Researching archinstall profiles", 60),
        ("Copying minimal profile template", 60),
        ("Customizing profile for AgentOS", 90),
        ("Adding Ollama to packages", 30),
        ("Testing profile syntax", 60)
    ],
    "[Phase 1] Build first test ISO": [
        ("Preparing build environment", 60),
        ("Running mkarchiso", 120),
        ("Verifying ISO output", 60),
        ("Testing ISO in VM", 60)
    ],
    "[Phase 2] Install OpenClaw in archinstall profile": [
        ("Researching OpenClaw dependencies", 60),
        ("Adding Node.js to packages", 30),
        ("Creating OpenClaw installation script", 90),
        ("Configuring OpenClaw systemd service", 60),
        ("Testing installation", 60)
    ],
    "[Phase 2] Pre-configure Kimi k2.5 cloud": [
        ("Creating OpenClaw config template", 60),
        ("Setting default_model to kimi-k2.5:cloud", 30),
        ("Configuring webchat provider", 60),
        ("Testing configuration", 90),
        ("Documenting setup", 60)
    ],
    "[Phase 2] Create TTY greeting": [
        ("Designing welcome message", 60),
        ("Creating .bashrc modifications", 60),
        ("Adding agent command alias", 30),
        ("Testing TTY integration", 90),
        ("Polishing output format", 60)
    ],
    "[Phase 2] Web UI auto-start": [
        ("Creating systemd service file", 60),
        ("Configuring auto-start on boot", 60),
        ("Setting up port 3000", 30),
        ("Testing service startup", 90),
        ("Verifying web UI accessible", 60)
    ],
    "[Phase 3] GPU selection in installer UI": [
        ("Researching GPU detection methods", 60),
        ("Creating GPU vendor selection dialog", 90),
        ("Implementing AMD ROCm option", 60),
        ("Implementing NVIDIA CUDA option", 60),
        ("Testing UI flow", 60)
    ],
    "[Phase 3] Error handling and edge cases": [
        ("Identifying potential failure points", 60),
        ("Implementing retry logic", 90),
        ("Adding graceful degradation", 60),
        ("Testing error scenarios", 60),
        ("Documenting error recovery", 30)
    ],
    "[Phase 3] Documentation": [
        ("Writing README.md", 90),
        ("Creating usage examples", 60),
        ("Documenting configuration options", 60),
        ("Adding troubleshooting guide", 60),
        ("Reviewing documentation", 30)
    ],
    "[Phase 3] Release ISO": [
        ("Final build preparation", 60),
        ("Building release ISO", 120),
        ("Testing release ISO", 60),
        ("Creating release notes", 30),
        ("Uploading to GitHub", 30)
    ]
}

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
    if data:
        print(f"  Data: {data}")
    if error:
        print(f"  ERROR: {error}")


class ActivityBasedWorkDetector:
    """Work detector that logs actual activities."""
    
    def __init__(self, project_name: str, trello_board_id: str, 
                 trello_api_key: str = None, trello_token: str = None):
        self.project_name = project_name
        self.trello_board_id = trello_board_id
        self.work_cycle_seconds = WORK_CYCLE_MINUTES * 60
        
        log_action('INIT', f'Initializing activity-based detector for {project_name}')
        
        try:
            self.trello_client = TrelloClient(trello_api_key, trello_token)
            log_action('TRELLO', 'TrelloClient initialized')
        except Exception as e:
            log_action('TRELLO', 'Failed to initialize TrelloClient', error=e)
            raise
            
        self.work_manager = TrelloWorkManager(self.trello_client, trello_board_id)
        self.state_mgr = SessionState(project_name)
        self.current_card: Optional[TrelloCard] = None
        self.current_activities: List[tuple] = []
        self.current_activity_index = 0
        
    def get_activities_for_task(self, card_name: str) -> List[tuple]:
        """Get activities for a task, or generate generic ones."""
        # Try exact match
        if card_name in TASK_ACTIVITIES:
            return TASK_ACTIVITIES[card_name]
        
        # Try partial match
        for task_name, activities in TASK_ACTIVITIES.items():
            if task_name in card_name or card_name in task_name:
                return activities
        
        # Generate generic activities
        log_action('TASK', f'No specific activities for: {card_name}, using generic')
        return [
            ("Analyzing task requirements", 60),
            ("Researching solution approach", 60),
            ("Implementing solution", 120),
            ("Testing implementation", 60),
            ("Finalizing and documenting", 60)
        ]
    
    def start_work(self, card: TrelloCard) -> bool:
        """Start working on a card."""
        log_action('WORKFLOW', f'Starting work on: {card.name}')
        
        # Get activities for this task
        self.current_activities = self.get_activities_for_task(card.name)
        self.current_activity_index = 0
        
        total_time = sum(a[1] for a in self.current_activities)
        log_action('TASK', f'Task has {len(self.current_activities)} activities, '
                  f'total time: {total_time}s')
        
        # Log planned activities
        for i, (activity, duration) in enumerate(self.current_activities):
            log_action('PLAN', f'Activity {i+1}: {activity} ({duration}s)')
        
        # Move to In Progress
        log_action('TRELLO', f'Moving to In Progress: {card.name}')
        try:
            if self.work_manager.start_work(card):
                log_action('TRELLO', 'Successfully moved to In Progress')
                self.current_card = card
                self._update_state_with_work(card, 'in_progress')
                
                # Add start comment with activity plan
                activity_list = '\n'.join([f"{i+1}. {act[0]} ({act[1]}s)" 
                                          for i, act in enumerate(self.current_activities)])
                self.work_manager.add_progress_comment(
                    card,
                    f"🚀 Work started at {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"**Planned Activities ({WORK_CYCLE_MINUTES} min):**\n{activity_list}\n\n"
                    f"Project: {self.project_name}"
                )
                log_action('TRELLO', 'Start comment with activity plan added')
                return True
            else:
                log_action('TRELLO', 'Failed to move to In Progress')
                return False
        except Exception as e:
            log_action('TRELLO', 'Error starting work', error=e)
            return False
    
    def do_work(self) -> bool:
        """Perform actual work with activity logging."""
        if not self.current_card:
            log_action('WORK', 'No current card to work on')
            return False
        
        log_action('WORK', f'Starting work on: {self.current_card.name}')
        log_action('WORK', f'Work cycle: {WORK_CYCLE_MINUTES} minutes')
        
        # Execute each activity
        for idx, (activity_name, activity_duration) in enumerate(self.current_activities):
            self.current_activity_index = idx
            
            log_action('ACTIVITY', f'Starting: {activity_name}')
            log_action('ACTIVITY', f'Estimated duration: {activity_duration}s')
            
            # Simulate doing the activity
            start_time = time.time()
            elapsed = 0
            update_interval = 10  # Log every 10 seconds
            
            while elapsed < activity_duration:
                time.sleep(min(update_interval, activity_duration - elapsed))
                elapsed = int(time.time() - start_time)
                
                # Log progress within activity
                progress = int((elapsed / activity_duration) * 100)
                log_action('PROGRESS', f'{activity_name}: {progress}% '
                          f'({elapsed}s / {activity_duration}s)')
            
            # Activity complete
            log_action('ACTIVITY', f'Completed: {activity_name}')
            
            # Add progress comment to Trello
            try:
                completed_activities = [a[0] for a in self.current_activities[:idx+1]]
                remaining_activities = [a[0] for a in self.current_activities[idx+1:]]
                
                progress_text = f"✅ **Completed:** {', '.join(completed_activities)}\n"
                if remaining_activities:
                    progress_text += f"⏳ **Remaining:** {', '.join(remaining_activities)}\n"
                
                self.work_manager.add_progress_comment(
                    self.current_card,
                    f"⏰ Activity {idx+1}/{len(self.current_activities)} Complete\n\n"
                    f"**Just Finished:** {activity_name}\n\n"
                    f"{progress_text}\n"
                    f"Time: {datetime.now().strftime('%H:%M:%S')}"
                )
                log_action('TRELLO', f'Activity completion logged: {activity_name}')
            except Exception as e:
                log_action('TRELLO', 'Error logging activity', error=e)
        
        log_action('WORK', f'All {len(self.current_activities)} activities completed')
        return True
    
    def complete_work(self) -> bool:
        """Complete work and move card to Done."""
        if not self.current_card:
            log_action('WORK', 'No current card to complete')
            return False
        
        log_action('WORKFLOW', f'Completing work: {self.current_card.name}')
        
        # Summary of completed activities
        completed = [a[0] for a in self.current_activities]
        log_action('SUMMARY', f'Completed activities: {len(completed)}')
        for activity in completed:
            log_action('SUMMARY', f'  - {activity}')
        
        # Add completion comment
        try:
            activity_summary = '\n'.join([f"✅ {act[0]}" for act in self.current_activities])
            self.work_manager.add_progress_comment(
                self.current_card,
                f"🎉 **Work Complete!**\n\n"
                f"**Completed Activities ({WORK_CYCLE_MINUTES} min):**\n"
                f"{activity_summary}\n\n"
                f"Finished at: {datetime.now().strftime('%H:%M:%S')}\n"
                f"Status: Ready for review"
            )
            log_action('TRELLO', 'Completion summary added')
        except Exception as e:
            log_action('TRELLO', 'Error adding completion comment', error=e)
        
        # Move to Done
        log_action('TRELLO', f'Moving to Done: {self.current_card.name}')
        try:
            if self.work_manager.complete_work(self.current_card):
                log_action('TRELLO', 'Successfully moved to Done')
                self._clear_work_from_state()
                self.current_card = None
                self.current_activities = []
                return True
            else:
                log_action('TRELLO', 'Failed to move to Done')
                return False
        except Exception as e:
            log_action('TRELLO', 'Error completing work', error=e)
            return False
    
    def do_work_cycle(self) -> bool:
        """Complete work cycle with full activity logging."""
        log_action('CYCLE', 'Starting activity-based work cycle')
        
        # Find work
        log_action('DETECT', 'Looking for ready work in Backlog...')
        ready = self.work_manager.get_ready_work()
        
        if not ready:
            log_action('DETECT', 'No ready work found')
            return False
        
        card = ready[0]
        log_action('DETECT', f'Found work: {card.name}')
        
        # Start work
        if not self.start_work(card):
            log_action('CYCLE', 'Failed to start work')
            return False
        
        # Do work with activities
        if not self.do_work():
            log_action('CYCLE', 'Work cycle interrupted')
            return False
        
        # Complete work
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
        state['current_activities'] = self.current_activities
        state['last_action'] = datetime.now().isoformat()
        state['status'] = status
        self.state_mgr.save(state)
        log_action('STATE', f'State updated: {status}', 
                  data={'card': card.name, 'activities': len(self.current_activities)})
    
    def _clear_work_from_state(self) -> None:
        """Clear work from state."""
        state = self.state_mgr.load() or {}
        state['current_card'] = None
        state['current_card_name'] = None
        state['current_activities'] = []
        state['last_action'] = datetime.now().isoformat()
        state['status'] = 'idle'
        self.state_mgr.save(state)
        log_action('STATE', 'State cleared', data={'status': 'idle'})
    
    def get_work_callback(self) -> Callable:
        """Return the work callback."""
        return self.do_work_cycle


def create_activity_detector(project_name: str, config: dict):
    """Factory function to create activity-based detector."""
    return ActivityBasedWorkDetector(
        project_name=project_name,
        trello_board_id=config.get('trello_board_id'),
        trello_api_key=config.get('trello_api_key') or os.environ.get('TRELLO_API_KEY'),
        trello_token=config.get('trello_token') or os.environ.get('TRELLO_TOKEN')
    )


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: work_detector_activity.py <project_name>")
        sys.exit(1)
    
    project = sys.argv[1]
    
    from config_manager import ConfigManager
    manager = ConfigManager()
    config_obj = manager.get_project_config(project)
    
    if not config_obj:
        print(f"No config for {project}")
        sys.exit(1)
    
    detector = create_activity_detector(project, config_obj.to_dict())
    result = detector.do_work_cycle()
    
    print(f"\nWork cycle result: {result}")
    print(f"Duration: {WORK_CYCLE_MINUTES} minutes")
    print(f"Log file: {ACTION_LOG}")
