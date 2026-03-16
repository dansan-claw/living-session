#!/usr/bin/env python3
"""
Living Session - Work Detector

Intelligent work selection and management for living sessions.
Integrates Trello with the living session engine.
"""

import os
from typing import Optional, Callable
from datetime import datetime

from session_state import SessionState
from trello_client import TrelloClient, TrelloWorkManager, TrelloCard
from living_session import LivingSession


class LivingSessionWorkDetector:
    """
    Bridges Trello work management with living session consciousness.
    
    This is the brain that decides what to work on and manages the workflow.
    """
    
    def __init__(self, project_name: str, trello_board_id: str, 
                 trello_api_key: str = None, trello_token: str = None):
        self.project_name = project_name
        self.trello_board_id = trello_board_id
        
        # Initialize Trello client
        self.trello_client = TrelloClient(trello_api_key, trello_token)
        self.work_manager = TrelloWorkManager(self.trello_client, trello_board_id)
        
        # State management
        self.state_mgr = SessionState(project_name)
        
        # Current work tracking
        self.current_card: Optional[TrelloCard] = None
        
    def detect_work(self) -> bool:
        """
        Main work detection logic.
        
        Priority:
        1. Continue current work (In Progress)
        2. Start new ready work (Backlog with 🟢 Ready)
        3. Check for blocked items
        4. Sleep if nothing available
        
        Returns True if work was found/continued, False if no work.
        """
        print(f"\n🔍 [{datetime.now().strftime('%H:%M:%S')}] Detecting work...")
        
        # Priority 1: Check for blocked items (alert user)
        blocked = self.work_manager.get_blocked_work()
        if blocked:
            print(f"⚠️  Found {len(blocked)} blocked item(s)!")
            for card in blocked:
                print(f"   🔴 {card.name}")
            # Continue to find actual work, but user should know about blockers
        
        # Priority 2: Continue current work
        current = self.work_manager.get_current_work()
        if current:
            if self.current_card and self.current_card.id == current.id:
                print(f"  → Continuing: {current.name}")
            else:
                print(f"  → Resumed: {current.name}")
                self.current_card = current
                self._update_state_with_work(current)
            return True
        
        # Priority 3: Start new work
        next_work = self.work_manager.find_next_work()
        if next_work:
            print(f"  → Starting new: {next_work.name}")
            
            # Move to In Progress
            if self.work_manager.start_work(next_work):
                self.current_card = next_work
                self._update_state_with_work(next_work)
                
                # Add comment that we started
                self.work_manager.add_progress_comment(
                    next_work,
                    f"🚀 Living session started work on this task\n\n"
                    f"Project: {self.project_name}\n"
                    f"Time: {datetime.now().isoformat()}"
                )
                return True
            else:
                print(f"  ❌ Failed to start work")
                return False
        
        # No work available
        print(f"  ⏭️  No work available")
        return False
        
    def do_work_cycle(self) -> bool:
        """
        Perform one complete work cycle.
        
        This is the callback passed to LivingSession.
        """
        # Detect what to work on
        if not self.detect_work():
            return False
            
        # In a real implementation, this would:
        # 1. Read the card description
        # 2. Execute the task (e.g., write code, run commands)
        # 3. Update Trello with progress
        # 4. Move to Done when complete
        
        # For now, simulate work being done
        print(f"  🔨 Working on: {self.current_card.name}")
        
        # Simulate work completion (in real use, this would be actual work)
        # For testing, we'll mark it complete after one cycle
        # In production, this would check if task is actually done
        
        # Add progress comment
        self.work_manager.add_progress_comment(
            self.current_card,
            f"✅ Work cycle completed\n\n"
            f"Progress: Task worked on\n"
            f"Time: {datetime.now().isoformat()}"
        )
        
        # Move to Done
        print(f"  ✅ Completing: {self.current_card.name}")
        self.work_manager.complete_work(self.current_card)
        
        # Clear current work
        self.current_card = None
        self._clear_work_from_state()
        
        return True
        
    def _update_state_with_work(self, card: TrelloCard) -> None:
        """Update session state with current work."""
        state = self.state_mgr.load() or {}
        state['current_card'] = card.id
        state['current_card_name'] = card.name
        state['last_action'] = datetime.now().isoformat()
        state['status'] = 'working'
        self.state_mgr.save(state)
        
    def _clear_work_from_state(self) -> None:
        """Clear current work from session state."""
        state = self.state_mgr.load() or {}
        state['current_card'] = None
        state['current_card_name'] = None
        state['last_action'] = datetime.now().isoformat()
        state['status'] = 'idle'
        self.state_mgr.save(state)
        
    def get_work_callback(self) -> Callable:
        """Return the work callback for LivingSession."""
        return self.do_work_cycle
        
    def get_status(self) -> dict:
        """Get current work detector status."""
        return {
            'project': self.project_name,
            'board_id': self.trello_board_id,
            'current_card': self.current_card.name if self.current_card else None,
            'has_work': self.work_manager.has_work_available(),
            'has_blocked': self.work_manager.has_blocked_items()
        }


def create_living_session_with_trello(project_name: str, config: dict) -> LivingSession:
    """
    Factory function to create a fully configured living session.
    
    Creates a LivingSession with Trello work detection integrated.
    """
    # Create the living session
    session = LivingSession(project_name, config)
    
    # Create the work detector
    detector = LivingSessionWorkDetector(
        project_name=project_name,
        trello_board_id=config.get('trello_board_id'),
        trello_api_key=config.get('trello_api_key') or os.environ.get('TRELLO_API_KEY'),
        trello_token=config.get('trello_token') or os.environ.get('TRELLO_TOKEN')
    )
    
    # Connect work detector to session
    session.set_work_callback(detector.get_work_callback())
    
    return session


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: work_detector.py <command> [project_name]")
        print("Commands: detect, status, test")
        sys.exit(1)
        
    command = sys.argv[1]
    project = sys.argv[2] if len(sys.argv) > 2 else "living-session-skill"
    
    # Config for testing
    config = {
        'trello_board_id': '69b8427f2abeee3ed8649844',  # Living Session board
        'interval': 10,
        'trello_api_key': os.environ.get('TRELLO_API_KEY'),
        'trello_token': os.environ.get('TRELLO_TOKEN')
    }
    
    if command == "detect":
        print(f"🔍 Detecting work for '{project}'...")
        detector = LivingSessionWorkDetector(
            project, 
            config['trello_board_id'],
            config['trello_api_key'],
            config['trello_token']
        )
        has_work = detector.detect_work()
        print(f"\nResult: {'Work found' if has_work else 'No work'}")
        
    elif command == "status":
        detector = LivingSessionWorkDetector(
            project,
            config['trello_board_id'],
            config['trello_api_key'],
            config['trello_token']
        )
        status = detector.get_status()
        print(f"\n📊 Work Detector Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
            
    elif command == "test":
        print(f"🧪 Testing full work cycle...")
        session = create_living_session_with_trello(project, config)
        
        # Run one cycle
        print("\n--- Running one work cycle ---")
        session.run_cycle()
        session.stop()
        
    else:
        print(f"Unknown command: {command}")
