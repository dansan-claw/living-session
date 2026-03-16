#!/usr/bin/env python3
"""
Living Session - Daemon

The heart that pumps the blood - continuously monitors schedule
and triggers work cycles at the right time.
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path

# Add skill directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scheduler import SelfScheduler
from work_detector import create_living_session_with_trello
from config_manager import ConfigManager


class LivingSessionDaemon:
    """
    Daemon process that keeps the living session alive.
    
    Continuously monitors the schedule file and triggers
    work cycles at the appropriate times.
    """
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.running = False
        self.config = self._load_config()
        self.scheduler = SelfScheduler(project_name, self.config)
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _load_config(self) -> dict:
        """Load configuration for the project."""
        manager = ConfigManager()
        config_obj = manager.get_project_config(self.project_name)
        if config_obj:
            return config_obj.to_dict()
        else:
            print(f"❌ No configuration found for '{self.project_name}'")
            sys.exit(1)
            
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down daemon...")
        self.running = False
        
    def run(self) -> None:
        """
        Main daemon loop.
        
        Continuously:
        1. Check if it's time to wake
        2. If yes, execute work cycle
        3. If no, sleep until next check
        4. Repeat forever
        """
        print(f"\n🩸 Living Session Daemon Started")
        print(f"   Project: {self.project_name}")
        print(f"   PID: {os.getpid()}")
        print(f"   Press Ctrl+C to stop\n")
        
        self.running = True
        
        try:
            while self.running:
                # Check if another instance is already running
                if self.scheduler.is_running():
                    print(f"⏭️  [{self._timestamp()}] Another instance detected, waiting...")
                    time.sleep(60)
                    continue
                
                # Check if it's time to wake
                if self.scheduler.should_wake():
                    print(f"\n🌅 [{self._timestamp()}] Time to wake!")
                    
                    # Create session and execute work
                    session = create_living_session_with_trello(
                        self.project_name, 
                        self.config
                    )
                    
                    # Run work cycle with scheduling
                    result = self.scheduler.run_with_scheduling(
                        session.work_callback
                    )
                    
                    print(f"✅ [{self._timestamp()}] Work cycle complete: {result}\n")
                    
                    # Short pause before next check
                    time.sleep(5)
                    
                else:
                    # Not time yet, sleep until next check
                    seconds_until = self.scheduler.get_time_until_wake()
                    
                    if seconds_until is not None and seconds_until > 0:
                        # Sleep until 10 seconds before wake time
                        sleep_time = max(1, min(seconds_until - 10, 60))
                        print(f"💤 [{self._timestamp()}] Sleeping for {sleep_time}s "
                              f"(wake in {seconds_until}s)")
                        time.sleep(sleep_time)
                    else:
                        # No schedule set, check again in 1 minute
                        print(f"⏳ [{self._timestamp()}] No schedule, checking again in 60s")
                        time.sleep(60)
                        
        except KeyboardInterrupt:
            print(f"\n🛑 Daemon interrupted")
        finally:
            self.stop()
            
    def stop(self) -> None:
        """Stop the daemon gracefully."""
        print(f"\n🛑 Daemon stopped")
        self.running = False
        
    def _timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().strftime('%H:%M:%S')


def start_daemon(project_name: str) -> int:
    """Start the daemon for a project."""
    # Check if already running
    scheduler = SelfScheduler(project_name, {})
    if scheduler.is_running():
        print(f"⚠️  Daemon for '{project_name}' is already running!")
        return 1
        
    daemon = LivingSessionDaemon(project_name)
    daemon.run()
    return 0


def stop_daemon(project_name: str) -> int:
    """Stop the daemon for a project."""
    # Find PID from lock file
    lock_file = Path.home() / '.openclaw' / 'workspace' / '.living-sessions' / project_name / '.lock'
    
    if not lock_file.exists():
        print(f"⚠️  No daemon running for '{project_name}'")
        return 0
        
    try:
        with open(lock_file) as f:
            pid = int(f.read().strip())
            
        print(f"🛑 Stopping daemon (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)
        print(f"✅ Daemon stopped")
        return 0
        
    except (ValueError, ProcessLookupError):
        print(f"⚠️  Daemon not running (stale lock file)")
        lock_file.unlink(missing_ok=True)
        return 0


def daemon_status(project_name: str) -> int:
    """Check if daemon is running."""
    scheduler = SelfScheduler(project_name, {})
    
    if scheduler.is_running():
        print(f"🟢 Daemon for '{project_name}' is RUNNING")
        
        # Show schedule info
        seconds_until = scheduler.get_time_until_wake()
        if seconds_until is not None:
            mins = seconds_until // 60
            print(f"   Next wake: in {seconds_until}s ({mins}m)")
        return 0
    else:
        print(f"⚪ Daemon for '{project_name}' is NOT RUNNING")
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Living Session Daemon')
    parser.add_argument('command', choices=['start', 'stop', 'status'])
    parser.add_argument('project', help='Project name')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        sys.exit(start_daemon(args.project))
    elif args.command == 'stop':
        sys.exit(stop_daemon(args.project))
    elif args.command == 'status':
        sys.exit(daemon_status(args.project))
