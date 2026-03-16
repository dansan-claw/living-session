#!/usr/bin/env python3
"""
Living Session - Daemon with Comprehensive Logging

Logs all actions to file for debugging and monitoring.
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime

# Add skill directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scheduler import SelfScheduler
from work_detector import create_living_session_with_trello
from config_manager import ConfigManager

# Setup logging
LOG_FILE = Path.home() / '.openclaw' / 'workspace' / '.living-sessions' / 'daemon.log'

def log(message):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    # Append to log file
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')

class LoggingDaemon:
    """Daemon with detailed logging."""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.running = False
        log(f"Initializing daemon for project: {project_name}")
        
        self.config = self._load_config()
        self.scheduler = SelfScheduler(project_name, self.config)
        
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _load_config(self) -> dict:
        """Load configuration."""
        log("Loading configuration...")
        manager = ConfigManager()
        config_obj = manager.get_project_config(self.project_name)
        
        if config_obj:
            config = config_obj.to_dict()
            log(f"Config loaded: interval={config.get('interval')}s")
            return config
        else:
            log("ERROR: No configuration found!")
            sys.exit(1)
            
    def _signal_handler(self, signum, frame):
        log(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def run(self):
        log(f"🩸 Daemon started for {self.project_name}")
        log(f"PID: {os.getpid()}")
        log(f"Log file: {LOG_FILE}")
        
        self.running = True
        cycle_count = 0
        
        try:
            while self.running:
                cycle_count += 1
                log(f"\n=== Cycle {cycle_count} ===")
                
                # Check if another instance running
                if self.scheduler.is_running():
                    log("Another instance detected, waiting...")
                    time.sleep(60)
                    continue
                
                # Check schedule
                log("Checking if it's time to wake...")
                should_wake = self.scheduler.should_wake()
                log(f"Should wake: {should_wake}")
                
                if should_wake:
                    log("🌅 Time to wake! Starting work cycle...")
                    
                    # Create session
                    log("Creating living session...")
                    try:
                        session = create_living_session_with_trello(
                            self.project_name, 
                            self.config
                        )
                        log("Session created successfully")
                    except Exception as e:
                        log(f"ERROR creating session: {e}")
                        time.sleep(60)
                        continue
                    
                    # Run work cycle
                    log("Running work cycle...")
                    try:
                        result = self.scheduler.run_with_scheduling(
                            session.work_callback
                        )
                        log(f"Work cycle complete: {result}")
                    except Exception as e:
                        log(f"ERROR in work cycle: {e}")
                        import traceback
                        log(traceback.format_exc())
                    
                    log("Cycle complete, checking schedule...")
                    
                else:
                    # Not time yet
                    seconds_until = self.scheduler.get_time_until_wake()
                    if seconds_until is not None and seconds_until > 0:
                        sleep_time = max(1, min(seconds_until - 10, 60))
                        log(f"💤 Sleeping {sleep_time}s (wake in {seconds_until}s)")
                        time.sleep(sleep_time)
                    else:
                        log("⏳ No schedule, checking again in 60s")
                        time.sleep(60)
                        
        except KeyboardInterrupt:
            log("Interrupted by user")
        except Exception as e:
            log(f"FATAL ERROR: {e}")
            import traceback
            log(traceback.format_exc())
        finally:
            log("Daemon stopped")
            
    def stop(self):
        log("Stopping daemon...")
        self.running = False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project', help='Project name')
    args = parser.parse_args()
    
    daemon = LoggingDaemon(args.project)
    daemon.run()
