#!/usr/bin/env python3
"""
Living Session - Error Handling and Recovery

Resilient error handling with logging to .learnings/
"""

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Any
from enum import Enum
import time


class ErrorSeverity(Enum):
    """Error severity levels."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LivingSessionError(Exception):
    """Base exception for living session errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR,
                 recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.recoverable = recoverable
        self.timestamp = datetime.now().isoformat()


class TrelloAPIError(LivingSessionError):
    """Trello API specific errors."""
    pass


class ConfigError(LivingSessionError):
    """Configuration errors."""
    pass


class StateError(LivingSessionError):
    """State management errors."""
    pass


class ErrorLogger:
    """Logs errors to .learnings/ directory for self-improvement."""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.learnings_dir = Path.home() / ".openclaw" / "workspace" / ".learnings"
        self.errors_file = self.learnings_dir / "ERRORS.md"
        self._ensure_learnings_dir()
        
    def _ensure_learnings_dir(self) -> None:
        """Create .learnings directory if it doesn't exist."""
        self.learnings_dir.mkdir(parents=True, exist_ok=True)
        
        # Create ERRORS.md if it doesn't exist
        if not self.errors_file.exists():
            with open(self.errors_file, 'w') as f:
                f.write("# Errors Log\n\n")
                f.write("Command failures, exceptions, and unexpected behaviors.\n\n")
                f.write("---\n\n")
                
    def log_error(self, error: Exception, context: str = "") -> None:
        """
        Log an error to ERRORS.md.
        
        Format follows self-improvement skill pattern.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Determine error type and severity
        if isinstance(error, LivingSessionError):
            severity = error.severity.value
            recoverable = error.recoverable
            error_type = error.__class__.__name__
        else:
            severity = ErrorSeverity.ERROR.value
            recoverable = True
            error_type = error.__class__.__name__
            
        # Build error entry
        entry = f"""## {timestamp} - {error_type}

**Tool:** Living Session ({self.project_name})  
**Context:** {context or 'General operation'}

**Error:** {str(error)}

**Severity:** {severity}  
**Recoverable:** {'Yes' if recoverable else 'No'}

**Traceback:**
```
{traceback.format_exc()}
```

**Root Cause:** (To be determined)

**Solution:** (To be determined)

**Prevention:** (To be determined)

---

"""
        
        # Append to file
        with open(self.errors_file, 'a') as f:
            f.write(entry)
            
        print(f"📝 Error logged to: {self.errors_file}")
        
    def log_recovery(self, message: str) -> None:
        """Log a successful recovery."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        entry = f"""## {timestamp} - Recovery

**Status:** ✅ Recovered  
**Message:** {message}

---

"""
        with open(self.errors_file, 'a') as f:
            f.write(entry)


class RetryWithBackoff:
    """Retry mechanism with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: int = 1,
                 max_delay: int = 60):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Returns the function result or raises the last exception.
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    
                    print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                    print(f"   Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"❌ All {self.max_retries} attempts failed")
                    
        raise last_exception


class ResilientSession:
    """
    Wraps a living session with error handling and recovery.
    
    Ensures the session never loses consciousness permanently.
    """
    
    def __init__(self, project_name: str, config: dict):
        self.project_name = project_name
        self.config = config
        self.error_logger = ErrorLogger(project_name)
        self.retry = RetryWithBackoff(
            max_retries=config.get('retry_attempts', 3),
            base_delay=config.get('retry_delay', 60)
        )
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
    def run_with_resilience(self, work_func: Callable) -> bool:
        """
        Run work function with full error handling.
        
        This is the bulletproof wrapper that ensures continuity.
        """
        try:
            # Attempt work with retry
            result = self.retry.execute(work_func)
            
            # Success - reset error counter
            if result:
                self.consecutive_errors = 0
            
            return result
            
        except Exception as e:
            self.consecutive_errors += 1
            
            # Log the error
            self.error_logger.log_error(
                e,
                context=f"Work cycle (consecutive errors: {self.consecutive_errors})"
            )
            
            # Check if we've hit too many consecutive errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                print(f"🚨 Too many consecutive errors ({self.consecutive_errors})")
                print(f"   Pausing session for manual intervention")
                raise CriticalError(f"Session exceeded max consecutive errors: {e}")
                
            # Return False to indicate work not done, but session continues
            return False
            
    def recover_from_crash(self) -> bool:
        """
        Attempt to recover from a crash.
        
        Called on session startup to resume from last state.
        """
        from session_state import SessionState
        
        print("🔄 Attempting crash recovery...")
        
        state_mgr = SessionState(self.project_name)
        state = state_mgr.load()
        
        if not state:
            print("  ℹ️  No previous state found, starting fresh")
            return True
            
        # Check if we were in the middle of work
        if state.get('status') == 'working' and state.get('current_card'):
            print(f"  📝 Found interrupted work: {state.get('current_card_name')}")
            print(f"  ℹ️  Will resume on next cycle")
            
            # Log recovery
            self.error_logger.log_recovery(
                f"Recovered from crash, found interrupted work: {state.get('current_card_name')}"
            )
            
        return True


class CriticalError(Exception):
    """Critical error that requires manual intervention."""
    pass


# Decorator for resilient function execution
def resilient(max_retries: int = 3, log_errors: bool = True):
    """Decorator to make a function resilient to failures."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            retry = RetryWithBackoff(max_retries=max_retries)
            try:
                return retry.execute(func, *args, **kwargs)
            except Exception as e:
                if log_errors:
                    # Get project name from args if available
                    project_name = kwargs.get('project_name', 'unknown')
                    logger = ErrorLogger(project_name)
                    logger.log_error(e, context=func.__name__)
                raise
        return wrapper
    return decorator


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: error_handler.py <command>")
        print("Commands: test-error, test-retry, test-recovery")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "test-error":
        print("🧪 Testing error logging...")
        logger = ErrorLogger("test-project")
        
        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            logger.log_error(e, context="Test operation")
            print("✅ Error logged")
            
    elif command == "test-retry":
        print("🧪 Testing retry mechanism...")
        retry = RetryWithBackoff(max_retries=3, base_delay=1)
        
        attempt = 0
        def flaky_function():
            global attempt
            attempt += 1
            if attempt < 3:
                raise ConnectionError(f"Simulated failure (attempt {attempt})")
            return "Success!"
            
        try:
            result = retry.execute(flaky_function)
            print(f"✅ Result: {result}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            
    elif command == "test-recovery":
        print("🧪 Testing crash recovery...")
        
        # Create a mock state
        from session_state import SessionState, create_initial_state
        
        state_mgr = SessionState("test-recovery")
        state = create_initial_state("test-recovery", "board-123", {})
        state['status'] = 'working'
        state['current_card'] = 'card-123'
        state['current_card_name'] = 'Test Card'
        state_mgr.save(state)
        
        # Test recovery
        resilient_session = ResilientSession("test-recovery", {})
        resilient_session.recover_from_crash()
        
        print("✅ Recovery test complete")
        
    else:
        print(f"Unknown command: {command}")
