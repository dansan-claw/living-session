#!/usr/bin/env python3
"""
Living Session - Work/Sleep Cycle Engine

The heart of the living session - manages consciousness loop.
"""

import signal
import sys
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional, Dict, Any

from session_state import SessionState, create_initial_state


class SessionStatus(Enum):
    """Session status states."""
    INITIALIZED = "initialized"
    AWAKE = "awake"
    WORKING = "working"
    SLEEPING = "sleeping"
    PAUSED = "paused"
    STOPPED = "stopped"


class LivingSession:
    """
    Manages the work/sleep cycle of a living session.
    
    Implements the consciousness loop:
    Wake -> Work -> Sleep -> Repeat
    """
    
    def __init__(self, project_name: str, config: Dict[str, Any]):
        self.project_name = project_name
        self.config = config
        self.state_mgr = SessionState(project_name)
        self.status = SessionStatus.INITIALIZED
        self.running = False
        self.current_interval = config.get('interval', 3600)
        self.work_callback: Optional[Callable] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def set_work_callback(self, callback: Callable) -> None:
        """
        Set the callback function that performs work.
        
        The callback should return:
        - True if work was done
        - False if no work available
        """
        self.work_callback = callback
        
    def wake(self) -> bool:
        """
        Wake up - load state and prepare for work.
        
        Returns True if session should continue, False otherwise.
        """
        print(f"\n🌅 [{datetime.now().strftime('%H:%M:%S')}] Waking up...")
        
        # Load existing state or create new
        state = self.state_mgr.load()
        if state is None:
            print(f"🆕 No existing state found, creating new session for '{self.project_name}'")
            # Note: In real implementation, we'd get trello_board_id from config
            state = create_initial_state(
                self.project_name,
                self.config.get('trello_board_id', ''),
                self.config
            )
            self.state_mgr.save(state)
        else:
            print(f"📂 Loaded state from: {self.state_mgr.get_state_path()}")
            
        self.status = SessionStatus.AWAKE
        return True
        
    def work(self) -> bool:
        """
        Perform work cycle.
        
        Returns True if work was done, False if no work available.
        """
        if not self.work_callback:
            print("⚠️  No work callback set, skipping work cycle")
            return False
            
        self.status = SessionStatus.WORKING
        print(f"🔨 Starting work cycle...")
        
        try:
            work_done = self.work_callback()
            if work_done:
                print(f"✅ Work completed")
                # Reset interval to default after successful work
                self.current_interval = self.config.get('interval', 3600)
            else:
                print(f"⏭️  No work available")
                # Increase interval if no work (up to max)
                max_interval = self.config.get('max_interval', 14400)
                self.current_interval = min(self.current_interval * 2, max_interval)
                
            return work_done
            
        except Exception as e:
            print(f"❌ Work cycle failed: {e}")
            return False
            
    def sleep(self) -> None:
        """Sleep until next wake cycle."""
        self.status = SessionStatus.SLEEPING
        wake_time = datetime.now() + timedelta(seconds=self.current_interval)
        
        print(f"💤 Sleeping for {self.current_interval}s...")
        print(f"⏰ Next wake: {wake_time.strftime('%H:%M:%S')}")
        
        # Sleep in small increments to allow interruption
        slept = 0
        while self.running and slept < self.current_interval:
            time.sleep(1)
            slept += 1
            
    def run_cycle(self) -> bool:
        """
        Run one complete cycle: Wake -> Work -> Sleep.
        
        Returns True if session should continue, False to stop.
        """
        if not self.wake():
            return False
            
        self.work()
        
        if self.running:
            self.sleep()
            
        return self.running
        
    def start(self) -> None:
        """Start the living session consciousness loop."""
        print(f"\n🩸 Starting living session: {self.project_name}")
        print(f"⏰ Interval: {self.current_interval}s")
        print(f"🛑 Press Ctrl+C to stop gracefully\n")
        
        self.running = True
        self.status = SessionStatus.AWAKE
        
        try:
            while self.running:
                if not self.run_cycle():
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            
        finally:
            self.stop()
            
    def stop(self) -> None:
        """Stop the living session gracefully."""
        print(f"\n🛑 Stopping living session: {self.project_name}")
        self.running = False
        self.status = SessionStatus.STOPPED
        
        # Save final state
        state = self.state_mgr.load() or {}
        state['status'] = 'stopped'
        state['stopped_at'] = datetime.now().isoformat()
        self.state_mgr.save(state)
        
        print(f"💾 Final state saved")
        print(f"🧠 Consciousness paused. Resume with: living-session resume {self.project_name}")
        
    def pause(self) -> None:
        """Pause the session (can be resumed)."""
        print(f"\n⏸️  Pausing living session: {self.project_name}")
        self.running = False
        self.status = SessionStatus.PAUSED
        
        state = self.state_mgr.load() or {}
        state['status'] = 'paused'
        state['paused_at'] = datetime.now().isoformat()
        self.state_mgr.save(state)
        
    def resume(self) -> None:
        """Resume a paused session."""
        print(f"\n▶️  Resuming living session: {self.project_name}")
        
        state = self.state_mgr.load()
        if state and state.get('status') == 'paused':
            state['status'] = 'resumed'
            state['resumed_at'] = datetime.now().isoformat()
            self.state_mgr.save(state)
            
        self.start()
        
    def get_status(self) -> Dict[str, Any]:
        """Get current session status."""
        state = self.state_mgr.load() or {}
        return {
            'project': self.project_name,
            'status': self.status.value,
            'running': self.running,
            'current_interval': self.current_interval,
            'state_file': str(self.state_mgr.get_state_path()),
            'last_action': state.get('last_action'),
            'current_card': state.get('current_card')
        }


# Example work callback for testing
def example_work_callback() -> bool:
    """Example work function - just prints and returns."""
    print("  → Doing example work...")
    time.sleep(2)  # Simulate work
    return True  # Work was done


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Living Session - Consciousness Engine")
    parser.add_argument("command", choices=["start", "stop", "status", "test"])
    parser.add_argument("project", nargs="?", default="test-project")
    parser.add_argument("--interval", type=int, default=10, help="Interval in seconds (default: 10)")
    
    args = parser.parse_args()
    
    config = {
        'interval': args.interval,
        'max_interval': 60,
        'trello_board_id': 'test-board'
    }
    
    session = LivingSession(args.project, config)
    
    if args.command == "start":
        session.set_work_callback(example_work_callback)
        session.start()
        
    elif args.command == "status":
        status = session.get_status()
        print(f"\n📊 Session Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
            
    elif args.command == "test":
        print("🧪 Testing living session (3 cycles)...")
        session.set_work_callback(example_work_callback)
        
        # Run 3 cycles then stop
        for i in range(3):
            if not session.run_cycle():
                break
        session.stop()
        
    else:
        print(f"Command '{args.command}' not yet implemented")
