#!/usr/bin/env python3
"""
Living Session - Fixed Scheduler

Always uses 5-minute intervals, no exponential backoff.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


class FixedScheduler:
    """Scheduler with fixed 5-minute intervals."""
    
    def __init__(self, project_name: str, config: Dict[str, Any]):
        self.project_name = project_name
        self.config = config
        
        # FIXED: Always 5 minutes
        self.interval = 300  # 5 minutes = 300 seconds
        
        self.scheduler_dir = Path.home() / ".openclaw" / "workspace" / ".living-sessions" / project_name
        self.schedule_file = self.scheduler_dir / "schedule.json"
        self.scheduler_dir.mkdir(parents=True, exist_ok=True)
        
    def save_schedule(self, next_wake: datetime, work_done: bool) -> None:
        """Save schedule - always 5 minutes."""
        schedule_data = {
            'project': self.project_name,
            'last_run': datetime.now().isoformat(),
            'next_wake': next_wake.isoformat(),
            'interval': self.interval,  # FIXED: Always 300
            'work_done': work_done,
        }
        
        # Atomic write
        temp_file = self.schedule_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        temp_file.rename(self.schedule_file)
        
    def load_schedule(self) -> Optional[Dict[str, Any]]:
        """Load scheduling state."""
        if not self.schedule_file.exists():
            return None
        try:
            with open(self.schedule_file, 'r') as f:
                return json.load(f)
        except:
            return None
            
    def calculate_next_wake(self) -> datetime:
        """Calculate next wake - FIXED 5 minutes."""
        now = datetime.now()
        next_wake = now + timedelta(seconds=self.interval)
        return next_wake
        
    def should_wake(self) -> bool:
        """Check if it's time to wake."""
        schedule = self.load_schedule()
        if not schedule:
            return True  # No schedule = wake immediately
        next_wake = datetime.fromisoformat(schedule['next_wake'])
        return datetime.now() >= next_wake
        
    def get_time_until_wake(self) -> Optional[int]:
        """Get seconds until next wake."""
        schedule = self.load_schedule()
        if not schedule:
            return None
        next_wake = datetime.fromisoformat(schedule['next_wake'])
        seconds = int((next_wake - datetime.now()).total_seconds())
        return max(0, seconds)
        
    def run_with_scheduling(self, work_func) -> bool:
        """Run work with fixed 5-minute scheduling."""
        # Execute work
        work_done = work_func()
        
        # FIXED: Always schedule next wake in 5 minutes
        next_wake = self.calculate_next_wake()
        self.save_schedule(next_wake, work_done)
        
        return work_done


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: scheduler_fixed.py <project_name>")
        sys.exit(1)
        
    project = sys.argv[1]
    
    scheduler = FixedScheduler(project, {'interval': 300})
    
    print(f"Fixed scheduler for {project}")
    print(f"Interval: {scheduler.interval}s (5 minutes)")
    print(f"Next wake: {scheduler.calculate_next_wake()}")
