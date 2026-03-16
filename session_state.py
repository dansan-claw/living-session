#!/usr/bin/env python3
"""
Living Session - Session State Manager

Handles persistence of session state across restarts.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class SessionState:
    """Manages living session state persistence."""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.state_dir = Path.home() / ".openclaw" / "workspace" / ".living-sessions" / project_name
        self.state_file = self.state_dir / "state.json"
        self.backup_file = self.state_dir / "state.json.bak"
        
    def ensure_state_dir(self) -> None:
        """Create state directory if it doesn't exist."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
    def save(self, state: Dict[str, Any]) -> bool:
        """
        Save session state atomically.
        
        Uses write-to-temp-then-rename pattern for atomicity.
        """
        try:
            self.ensure_state_dir()
            
            # Add timestamp
            state['last_saved'] = datetime.utcnow().isoformat()
            
            # Write to temp file
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # Backup existing state if it exists
            if self.state_file.exists():
                shutil.copy2(self.state_file, self.backup_file)
            
            # Atomic rename
            temp_file.rename(self.state_file)
            
            return True
            
        except Exception as e:
            print(f"Failed to save state: {e}")
            return False
            
    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load session state.
        
        Returns None if no state exists or state is corrupted.
        """
        try:
            if not self.state_file.exists():
                return None
                
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                
            # Validate required fields
            required = ['project', 'config']
            if not all(field in state for field in required):
                print("State file missing required fields, attempting recovery...")
                return self._recover_from_backup()
                
            return state
            
        except json.JSONDecodeError:
            print("State file corrupted, attempting recovery...")
            return self._recover_from_backup()
            
        except Exception as e:
            print(f"Failed to load state: {e}")
            return None
            
    def _recover_from_backup(self) -> Optional[Dict[str, Any]]:
        """Attempt to recover from backup file."""
        try:
            if self.backup_file.exists():
                print("Recovering from backup...")
                with open(self.backup_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Backup recovery failed: {e}")
            return None
            
    def exists(self) -> bool:
        """Check if state file exists."""
        return self.state_file.exists()
        
    def delete(self) -> bool:
        """Delete session state."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            if self.backup_file.exists():
                self.backup_file.unlink()
            return True
        except Exception as e:
            print(f"Failed to delete state: {e}")
            return False
            
    def get_state_path(self) -> Path:
        """Return path to state file."""
        return self.state_file


def create_initial_state(project_name: str, trello_board_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Create initial state for a new session."""
    return {
        "project": project_name,
        "trello_board_id": trello_board_id,
        "current_card": None,
        "last_action": None,
        "status": "initialized",
        "context": {
            "recent_findings": [],
            "blockers": [],
            "next_steps": []
        },
        "config": config,
        "created_at": datetime.utcnow().isoformat(),
        "last_saved": None
    }


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: session_state.py <command> [project_name]")
        print("Commands: test, show, delete")
        sys.exit(1)
        
    command = sys.argv[1]
    project = sys.argv[2] if len(sys.argv) > 2 else "test-project"
    
    state_mgr = SessionState(project)
    
    if command == "test":
        print(f"Testing session state for '{project}'...")
        
        # Create test state
        test_state = create_initial_state(
            project, 
            "test-board-123",
            {"interval": 3600, "auto_start": True}
        )
        
        # Save
        if state_mgr.save(test_state):
            print(f"State saved to: {state_mgr.get_state_path()}")
        else:
            print("Save failed")
            sys.exit(1)
            
        # Load
        loaded = state_mgr.load()
        if loaded:
            print(f"State loaded successfully")
            print(f"   Project: {loaded['project']}")
            print(f"   Status: {loaded['status']}")
        else:
            print("Load failed")
            sys.exit(1)
            
    elif command == "show":
        state = state_mgr.load()
        if state:
            print(json.dumps(state, indent=2))
        else:
            print(f"No state found for '{project}'")
            
    elif command == "delete":
        if state_mgr.delete():
            print(f"State deleted for '{project}'")
        else:
            print(f"Failed to delete state")
            
    else:
        print(f"Unknown command: {command}")
