# Living Session - Usage Examples

Comprehensive examples of using the living-session skill.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Project Setup](#project-setup)
3. [Advanced Configuration](#advanced-configuration)
4. [Integration Patterns](#integration-patterns)
5. [Troubleshooting Examples](#troubleshooting-examples)

---

## Basic Usage

### Example 1: Start Your First Living Session

```bash
# Navigate to the skill directory
cd ~/.openclaw/skills/living-session

# Start a session for your project
./living-session start my-project

# You'll see:
# 🩸 Starting living session: my-project
# ⏰ Interval: 3600s
# 🛑 Press Ctrl+C to stop gracefully
#
# 🌅 [14:32:10] Waking up...
# 📂 Loaded state from: /home/user/.openclaw/workspace/.living-sessions/my-project/state.json
# 🔨 Starting work cycle...
```

### Example 2: Check Session Status

```bash
./living-session status my-project

# Output:
# 📊 Living Session Status: my-project
# ────────────────────────────────────────
# 🟢 Status: AWAKE
# 📁 State: /home/user/.openclaw/workspace/.living-sessions/my-project/state.json
# 📋 Current task: [Phase 2] Implement feature X
# ⏰ Last action: 2026-03-16T14:30:00
# ⏳ Next wake: in 1800s
# 📈 Current interval: 3600s
# 🔄 Work cycles: 5
# 💤 No-work cycles: 0
# ────────────────────────────────────────
```

### Example 3: List All Sessions

```bash
./living-session list

# Output:
# 📋 Living Sessions
# ────────────────────────────────────────
# 🟢 agentos              (last: 2026-03-16)
# ⚪ my-website           (last: 2026-03-15)
# 🟢 research-project     (last: 2026-03-16)
# ⚪ old-project          (last: Never)
# ────────────────────────────────────────
```

---

## Project Setup

### Example 4: Configure a New Project

```bash
# Create configuration
python3 config_manager.py create my-new-project 69b1234567890abcdef \
  --interval 1800 \
  --auto-start

# Output:
# ✅ Created configuration for 'my-new-project'
#    Saved to: /home/user/.openclaw/config.yaml

# Verify it was created
python3 config_manager.py list

# Output:
# 📋 Configured Projects:
#   - my-new-project
#   - agentos
```

### Example 5: View Project Configuration

```bash
python3 config_manager.py show my-new-project

# Output:
# 📊 Configuration for 'my-new-project':
#   project_name: my-new-project
#   trello_board_id: 69b1234567890abcdef
#   trello_api_key: ***
#   trello_token: ***
#   interval: 1800
#   min_interval: 60
#   max_interval: 14400
#   auto_start: True
#   enable_chaining: False
```

### Example 6: Update Configuration

```python
# In Python
from config_manager import ConfigManager

manager = ConfigManager()
manager.update_project_config(
    'my-new-project',
    interval=3600,  # Change to 1 hour
    notify_on_blocked=False
)

# Output:
# ✅ Updated configuration for 'my-new-project'
```

---

## Advanced Configuration

### Example 7: Different Intervals for Different Work Types

```yaml
# ~/.openclaw/config.yaml
living_sessions:
  # Fast-paced development
  active-dev:
    trello_board_id: "board-1"
    interval: 900        # 15 minutes
    min_interval: 300     # 5 minutes minimum
    max_interval: 3600    # 1 hour maximum
    
  # Slow-burn research
  research:
    trello_board_id: "board-2"
    interval: 14400     # 4 hours
    min_interval: 3600    # 1 hour minimum
    max_interval: 86400   # 24 hours maximum
    
  # Monitoring only
  monitoring:
    trello_board_id: "board-3"
    interval: 86400      # Daily
    notify_on_blocked: true
```

### Example 8: Enable Session Chaining

```yaml
living_sessions:
  chained-project:
    trello_board_id: "board-xxx"
    interval: 3600
    enable_chaining: true  # Enable continuous chaining
```

```python
# In code
from scheduler import ChainedScheduler

scheduler = ChainedScheduler('chained-project', config)
scheduler.enable_chaining()

# Now sessions will automatically spawn next instance
```

---

## Integration Patterns

### Example 9: Custom Work Function

```python
from living_session import LivingSession
from work_detector import LivingSessionWorkDetector

def my_custom_work():
    """Custom work function that gets called each cycle."""
    
    # Check if there's work in your custom system
    if has_code_to_write():
        write_code()
        return True
        
    if has_tests_to_run():
        run_tests()
        return True
        
    return False

# Create session with custom work
session = LivingSession('my-project', config)
detector = LivingSessionWorkDetector('my-project', board_id)
detector.work_callback = my_custom_work
session.set_work_callback(detector.do_work_cycle)

session.start()
```

### Example 10: Integration with CI/CD

```yaml
# .github/workflows/living-session.yml
name: Living Session Monitor

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Check living session status
        run: |
          ~/.openclaw/skills/living-session/living-session status my-project
          
      - name: Restart if stopped
        if: failure()
        run: |
          ~/.openclaw/skills/living-session/living-session start my-project
```

### Example 11: Webhook Integration

```python
from flask import Flask, request
from living_session import LivingSession

app = Flask(__name__)

@app.route('/webhook/trello', methods=['POST'])
def trello_webhook():
    """Trigger immediate wake when Trello card updated."""
    
    # Parse webhook
    data = request.json
    
    # Wake up session immediately
    session = LivingSession('my-project', config)
    session.wake()
    
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(port=5000)
```

---

## Troubleshooting Examples

### Example 12: Debug Session Not Starting

```bash
# Step 1: Check if already running
./living-session status my-project

# Step 2: Validate configuration
python3 config_manager.py validate

# Step 3: Check Trello credentials
curl -s "https://api.trello.com/1/members/me?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN"

# Step 4: Test Trello connection
python3 trello_client.py test your-board-id

# Step 5: Check error logs
tail -50 ~/.openclaw/workspace/.learnings/ERRORS.md

# Step 6: Manual test
python3 living_session.py test my-project --interval 5
```

### Example 13: Recover from Crash

```bash
# Check if session crashed
./living-session status my-project
# ⚪ Status: ASLEEP (may indicate crash)

# Check error logs
tail ~/.openclaw/workspace/.learnings/ERRORS.md

# Look for recovery info
# You should see:
# ## 2026-03-16 14:30:00 - Recovery
# **Status:** ✅ Recovered
# **Message:** Recovered from crash, found interrupted work: [Phase 2] ...

# Resume session
./living-session resume my-project
```

### Example 14: Handle Blocked Items

```bash
# Session keeps alerting about blocked items
# Check what is blocked

python3 -c "
from trello_client import TrelloClient, TrelloWorkManager
import os

client = TrelloClient(
    os.environ['TRELLO_API_KEY'],
    os.environ['TRELLO_TOKEN']
)

manager = TrelloWorkManager(client, 'your-board-id')
blocked = manager.get_blocked_work()

print('🔴 Blocked items:')
for card in blocked:
    print(f'  - {card.name}')
    print(f'    URL: {card.short_url}')
"

# Output:
# 🔴 Blocked items:
#   - [Phase 3] Need API key from admin
#     URL: https://trello.com/c/xxx
#   - [Bug] Waiting for user feedback
#     URL: https://trello.com/c/yyy
```

### Example 15: Reset After Too Many Errors

```bash
# Session stopped due to too many consecutive errors
# Check error count

python3 -c "
from scheduler import SelfScheduler

scheduler = SelfScheduler('my-project', {})
status = scheduler.get_status()

print(f'Consecutive errors: {status.get(\"consecutive_errors\", 0)}')
print(f'Max allowed: 5')
"

# Reset by clearing state
rm -rf ~/.openclaw/workspace/.learnings/ERRORS.md
rm -rf ~/.openclaw/workspace/.living-sessions/my-project/

# Start fresh
./living-session start my-project
```

---

## Real-World Scenarios

### Scenario 1: Overnight Development

```bash
# 18:00 - Start session before leaving work
./living-session start agentos

# Session works through the night:
# 18:00 - Wake, work on Phase 1
# 18:45 - Complete Phase 1, sleep 1 hour
# 19:45 - Wake, work on Phase 2
# 20:30 - Complete Phase 2, sleep 1 hour
# ...

# 09:00 - Next morning, check progress
./living-session status agentos
# 🟢 Status: AWAKE
# 📋 Current task: [Phase 5] Documentation
# 🔄 Work cycles: 8
# ✅ 4 cards moved to Done
```

### Scenario 2: Weekend Project

```yaml
# Config for weekend project
living_sessions:
  weekend-project:
    trello_board_id: "board-xxx"
    interval: 7200      # 2 hours - relaxed pace
    min_interval: 3600  # 1 hour minimum
    max_interval: 21600 # 6 hours maximum
```

```bash
# Friday evening
./living-session start weekend-project

# Works all weekend at relaxed pace
# Checks every 2 hours, works if available
# Sleeps longer if no work

# Sunday evening
./living-session status weekend-project
# 🟢 Status: AWAKE
# 🔄 Work cycles: 12
# 💤 No-work cycles: 8
```

### Scenario 3: Multi-Project Management

```bash
# Terminal 1 - Active development
./living-session start agentos

# Terminal 2 - Side project
./living-session start personal-website

# Terminal 3 - Research
./living-session start research-project

# Check all
./living-session list
# 🟢 agentos              (active)
# 🟢 personal-website    (active)
# 🟢 research-project    (active)
```

---

## Tips and Best Practices

### Tip 1: Use Descriptive Card Names

```markdown
# Good
[Phase 2] Implement user authentication
[Bug] Fix memory leak in worker thread
[Research] Evaluate database options

# Bad
Update code
Fix stuff
Do research
```

### Tip 2: Label Cards Appropriately

- 🟢 **Ready** - Session will pick these up
- 🔴 **Blocked** - Session will alert you
- 🟡 **Research** - Session will investigate

### Tip 3: Monitor Error Logs

```bash
# Set up a daily check
0 9 * * * tail -20 ~/.openclaw/workspace/.learnings/ERRORS.md
```

### Tip 4: Use Status Command Regularly

```bash
# Add to your shell profile
alias lss='~/.openclaw/skills/living-session/living-session status'

# Now just type
lss my-project
```

---

## Need Help?

- Check [README.md](README.md) for overview
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- See [SKILL.md](SKILL.md) for OpenClaw integration
- File issues on GitHub

**Remember:** The blood keeps flowing! 🩸
