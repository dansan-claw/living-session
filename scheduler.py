#!/usr/bin/env python3
"""
Living Session - Self-Scheduling Mechanism

The heart of the living session - completion-based scheduling.
"""

import os
import time
import json
import fcntl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from enum import Enum


class ScheduleMode(Enum):
    """Scheduling modes."""
    COMPLETION_BASED = "completion"  # Schedule after work completes
    TIME_BASED = "time"              # Traditional cron-like
    HYBRID = "hybrid"                # Smart combination


class SelfScheduler:
    """
    Self-scheduling mechanism for living sessions.
    
    Implements completion-based scheduling where finishing work
triggers the next cycle - the "blood flow".
    """
    
    def __init__(self, project_name: str, config: Dict[str, Any]):
        self.project_name = project_name
        self.config = config
        
        # Scheduling settings
        self.base_interval = config.get('interval', 3600)
        self.max_interval = config.get('max_interval', 14400)
        self.min_interval = config.get('min_interval', 60)
        self.current_interval = self.base_interval
        
        # Mode
        self.mode = ScheduleMode.COMPLETION_BASED
        
        # State tracking
        self.scheduler_dir = Path.home() / ".openclaw" / "workspace" / ".living-sessions" / project_name
        self.schedule_file = self.scheduler_dir / "schedule.json"
        self.lock_file = self.scheduler_dir / ".lock"
        
        # Work tracking
        self.last_work_time: Optional[datetime] = None
        self.work_count = 0
        self.no_work_count = 0
        
        # Ensure directory exists
        self.scheduler_dir.mkdir(parents=True, exist_ok=True)
        
    def _acquire_lock(self) -> bool:
        """
        Acquire file lock to prevent overlapping executions.
        
        Returns True if lock acquired, False if another instance is running.
        """
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write PID to lock file
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            return True
            
        except (IOError, OSError):
            # Lock already held by another process
            return False
            
    def _release_lock(self) -> None:
        """Release file lock."""
        if hasattr(self, 'lock_fd') and self.lock_fd:
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
            self.lock_fd.close()
            
    def is_running(self) -> bool:
        """Check if another instance is currently running."""
        try:
            test_fd = open(self.lock_file, 'w')
            fcntl.flock(test_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(test_fd.fileno(), fcntl.LOCK_UN)
            test_fd.close()
            return False
        except (IOError, OSError):
            return True
            
    def calculate_next_wake(self, work_done: bool) -> datetime:
        """
        Calculate when to wake next based on work completion.
        
        This is the core of completion-based scheduling:
        - Work done → Normal interval
        - No work → Longer interval (up to max)
        - Many no-work cycles → Max interval
        """
        now = datetime.now()
        
        if work_done:
            # Reset to base interval after successful work
            self.current_interval = self.base_interval
            self.no_work_count = 0
            self.work_count += 1
        else:
            # Increase interval when no work available
            self.no_work_count += 1
            self.work_count = 0
            
            # Exponential backoff up to max
            self.current_interval = min(
                self.current_interval * 2,
                self.max_interval
            )
            
        next_wake = now + timedelta(seconds=self.current_interval)
        return next_wake
        
    def save_schedule(self, next_wake: datetime, work_done: bool) -> None:
        """Save scheduling state to file."""
        schedule_data = {
            'project': self.project_name,
            'last_run': datetime.now().isoformat(),
            'next_wake': next_wake.isoformat(),
            'current_interval': self.current_interval,
            'work_done': work_done,
            'work_count': self.work_count,
            'no_work_count': self.no_work_count,
            'mode': self.mode.value
        }
        
        # Atomic write
        temp_file = self.schedule_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
        temp_file.rename(self.schedule_file)
        
    def load_schedule(self) -> Optional[Dict[str, Any]]:
        """Load scheduling state from file."""
        if not self.schedule_file.exists():
            return None
            
        try:
            with open(self.schedule_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
            
    def should_wake(self) -> bool:
        """
        Check if it's time to wake up.
        
        Returns True if next_wake time has passed.
        """
        schedule = self.load_schedule()
        if not schedule:
            return True  # No schedule = wake immediately
            
        next_wake = datetime.fromisoformat(schedule['next_wake'])
        return datetime.now() >= next_wake
        
    def get_time_until_wake(self) -> Optional[int]:
        """
        Get seconds until next scheduled wake.
        
        Returns None if no schedule exists.
        """
        schedule = self.load_schedule()
        if not schedule:
            return None
            
        next_wake = datetime.fromisoformat(schedule['next_wake'])
        delta = (next_wake - datetime.now()).total_seconds()
        return int(max(0, delta))
        
    def run_with_scheduling(self, work_func: Callable[[], bool]) -> bool:
        """
        Run work function with self-scheduling.
        
        This is the main entry point - the "blood flow":
        1. Check if we should run (prevent overlap)
        2. Execute work
        3. Calculate next wake based on result
        4. Save schedule
        5. Return (next cycle will be triggered by next call)
        
        Returns True if work was done, False otherwise.
        """
        # Prevent overlapping executions
        if not self._acquire_lock():
            print(f"⏭️  Another instance is running, skipping this cycle")
            return False
            
        try:
            # Execute work
            print(f"\n🩸 [{datetime.now().strftime('%H:%M:%S')}] Heartbeat")
            work_done = work_func()
            
            # Calculate and save next wake
            next_wake = self.calculate_next_wake(work_done)
            self.save_schedule(next_wake, work_done)
            
            # Report
            if work_done:
                print(f"✅ Work complete, next wake: {next_wake.strftime('%H:%M:%S')} "
                      f"(in {self.current_interval}s)")
            else:
                print(f"⏭️  No work, next wake: {next_wake.strftime('%H:%M:%S')} "
                      f"(in {self.current_interval}s) [backoff]")
                      
            return work_done
            
        finally:
            self._release_lock()
            
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        schedule = self.load_schedule()
        
        return {
            'project': self.project_name,
            'mode': self.mode.value,
            'current_interval': self.current_interval,
            'base_interval': self.base_interval,
            'max_interval': self.max_interval,
            'work_count': self.work_count,
            'no_work_count': self.no_work_count,
            'is_running': self.is_running(),
            'next_wake_in': self.get_time_until_wake(),
            'last_run': schedule.get('last_run') if schedule else None
        }


class ChainedScheduler(SelfScheduler):
    """
    Advanced scheduler that chains sessions together.
    
    After completing work, automatically spawns the next session.
    This creates truly continuous consciousness.
    """
    
    def __init__(self, project_name: str, config: Dict[str, Any]):
        super().__init__(project_name, config)
        self.chain_file = self.scheduler_dir / ".chain"
        
    def enable_chaining(self) -> None:
        """Enable session chaining."""
        with open(self.chain_file, 'w') as f:
            f.write('enabled')
            
    def disable_chaining(self) -> None:
        """Disable session chaining."""
        if self.chain_file.exists():
            self.chain_file.unlink()
            
    def is_chaining_enabled(self) -> bool:
        """Check if chaining is enabled."""
        return self.chain_file.exists()
        
    def spawn_next_session(self) -> None:
        """
        Spawn the next session in the chain.
        
        This would integrate with OpenClaw's session spawning.
        For now, we save state for the next wake.
        """
        # In full implementation, this would:
        # 1. Use sessions_spawn to create next session
        # 2. Pass state to new session
        # 3. Current session ends
        
        # For now, we just save state for next wake
        pass


# CLI for testing
if __name__ == "__main__":
    import sys
    import random
    
    if len(sys.argv) < 2:
        print("Usage: scheduler.py <command> [project_name]")
        print("Commands: test, status, demo")
        sys.exit(1)
        
    command = sys.argv[1]
    project = sys.argv[2] if len(sys.argv) > 2 else "test-scheduler"
    
    config = {
        'interval': 5,  # 5 seconds for testing
        'max_interval': 30,
        'min_interval': 2
    }
    
    scheduler = SelfScheduler(project, config)
    
    if command == "test":
        print("🧪 Testing self-scheduler...")
        
        def example_work():
            # Simulate work (70% success rate)
            success = random.random() > 0.3
            if success:
                print("  → Work done!")
            else:
                print("  → No work available")
            return success
            
        # Run 5 cycles
        for i in range(5):
            print(f"\n--- Cycle {i+1} ---")
            scheduler.run_with_scheduling(example_work)
            time.sleep(1)  # Brief pause between cycles
            
        print("\n✅ Test complete")
        
    elif command == "status":
        status = scheduler.get_status()
        print(f"\n📊 Scheduler Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
            
    elif command == "demo":
        print("🎬 Demonstrating completion-based scheduling...")
        print("Pattern: Work → Normal interval → No work → Backoff\n")
        
        def alternating_work():
            # Alternate between work and no work
            scheduler.demo_counter = getattr(scheduler, 'demo_counter', 0) + 1
            has_work = scheduler.demo_counter % 2 == 1
            print(f"  → {'Work done!' if has_work else 'No work'}")
            return has_work
            
        for i in range(6):
            print(f"\n--- Cycle {i+1} ---")
            scheduler.run_with_scheduling(alternating_work)
            time.sleep(0.5)
            
    else:
        print(f"Unknown command: {command}")
