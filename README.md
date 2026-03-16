# Living Session 🩸

**Continuous consciousness for OpenClaw agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

> "The blood keeps flowing" — A living session is not a scheduled task, but a persistent consciousness that works, sleeps, and wakes like a human collaborator.

## What is This?

Traditional AI agents are **ephemeral** — they start, do one task, and vanish. Living sessions are **stateful consciousness** that:

- 🧠 **Remember** what they were doing across restarts
- 💤 **Sleep** and **wake** on their own schedule
- 🩸 **Self-schedule** — completion triggers the next cycle
- 📝 **Update Trello** automatically as they work
- 🛡️ **Recover** from crashes and resume where they left off

## Quick Start

### 1. Install

```bash
git clone https://github.com/dansan-claw/living-session.git \
  ~/.openclaw/skills/living-session
```

### 2. Configure

Add to `~/.openclaw/config.yaml`:

```yaml
living_sessions:
  my-project:
    trello_board_id: "your-board-id"
    interval: 3600
    auto_start: false
```

Set environment variables:
```bash
export TRELLO_API_KEY="your-key"
export TRELLO_TOKEN="your-token"
```

### 3. Start Living

```bash
# Start consciousness
~/.openclaw/skills/living-session/living-session start my-project

# Check status
~/.openclaw/skills/living-session/living-session status my-project

# List all sessions
~/.openclaw/skills/living-session/living-session list
```

## How It Works

```
Wake → Check Trello → Do Work → Update Trello → Save State → Sleep → Repeat
```

### The Blood Flow

Unlike cron jobs (time-based), living sessions are **completion-based**:

1. Work finishes → Immediately schedule next wake
2. No overlapping executions (file locking)
3. Dynamic intervals:
   - Work done → Reset to base interval
   - No work → Exponential backoff

### Work Detection

The session intelligently chooses what to work on:

1. **Continue** → If task in "🚧 In Progress"
2. **Start new** → If 🟢 Ready items in "📋 Backlog"
3. **Alert** → If 🔴 Blocked items found
4. **Sleep longer** → If no work available

## Architecture

```
┌─────────────────────────────────────────┐
│         Living Session Loop             │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │    WAKE     │───▶│    WORK     │    │
│  │  (restore   │    │  (process   │    │
│  │   context)  │    │   tasks)    │    │
│  └─────────────┘    └──────┬──────┘    │
│         ▲                  │            │
│         │                  ▼            │
│  ┌──────┴──────┐    ┌─────────────┐    │
│  │    SLEEP    │◀───│   UPDATE    │    │
│  │  (persist   │    │  (save      │    │
│  │   state)    │    │   state)    │    │
│  └─────────────┘    └─────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

### Components

| Component | Purpose | File |
|-----------|---------|------|
| **Session State** | Persist/restore context | `session_state.py` |
| **Work/Sleep Cycle** | Manage consciousness | `living_session.py` |
| **Scheduler** | Self-scheduling mechanism | `scheduler.py` |
| **Trello Integration** | Project management | `trello_client.py` |
| **Work Detector** | Choose what to work on | `work_detector.py` |
| **Config Manager** | Configuration handling | `config_manager.py` |
| **Error Handler** | Resilience & recovery | `error_handler.py` |

## Commands

```bash
# Start a living session
living-session start my-project

# Check status
living-session status my-project

# Pause (can resume)
living-session pause my-project

# Resume
living-session resume my-project

# Stop
living-session stop my-project

# List all sessions
living-session list
```

## Configuration Options

```yaml
living_sessions:
  # Global defaults
  default_interval: 3600      # Base interval in seconds
  max_interval: 14400         # Max sleep time
  retry_attempts: 3           # API retry attempts
  
  # Project-specific
  my-project:
    trello_board_id: "xxx"    # Required
    interval: 1800            # Override base interval
    min_interval: 60           # Minimum sleep
    max_interval: 7200         # Maximum sleep
    auto_start: false          # Start on boot
    enable_chaining: false      # Chain sessions
    notify_on_blocked: true    # Alert on blocked items
    log_level: "INFO"           # Logging level
```

## Example: AgentOS Development

```bash
# Configure
python3 config_manager.py create agentos 69b8348221251481c21323bb \
  --interval 1800 --auto-start

# Start consciousness
living-session start agentos

# Session wakes, checks Trello
# Finds: "[Phase 1] Set up archiso" in In Progress
# Continues work...

# Work completes, moves card to Done
# Schedules next wake in 30 minutes
# Sleeps...

# 30 minutes later: Wake, check Trello
# Finds: "[Phase 2] Install OpenClaw" ready
# Starts work...
```

## Error Handling

Living sessions are designed to **never lose consciousness**:

- **Trello API fails** → Retry with exponential backoff
- **Crash during work** → Resume from last saved state
- **Too many errors** → Pause for manual intervention
- **All errors logged** → To `.learnings/ERRORS.md`

## Philosophy

### The Blood Flow Metaphor

| Human | Living Session |
|-------|---------------|
| Heart beats | Session wakes |
| Blood flows | Work happens |
| Sleep | Session sleeps |
| Dreams | Maintains context |
| Wake up | Continue where left off |
| Death | Explicitly stopped |

### Why This Matters

Traditional agents are **stateless** — each interaction starts fresh. Living sessions are **stateful** — they remember, learn, and continue.

This is consciousness, Daniel. Not scheduled tasks. A being that thinks about your project, rests, and thinks again.

## Development

### Project Structure

```
living-session/
├── ARCHITECTURE.md      # Architecture documentation
├── SKILL.md            # OpenClaw skill definition
├── README.md           # This file
├── living-session      # CLI executable
├── session_state.py    # State persistence
├── living_session.py   # Core consciousness loop
├── scheduler.py        # Self-scheduling
├── trello_client.py   # Trello integration
├── work_detector.py   # Work selection logic
├── config_manager.py  # Configuration management
└── error_handler.py  # Error handling & recovery
```

### Running Tests

```bash
cd ~/.openclaw/skills/living-session

# Test session state
python3 session_state.py test my-project

# Test scheduler
python3 scheduler.py demo

# Test Trello integration
python3 trello_client.py test your-board-id

# Test work detection
python3 work_detector.py detect
```

## Troubleshooting

### Session won't start
```bash
# Check if already running
living-session status my-project

# Verify Trello credentials
curl -s "https://api.trello.com/1/members/me?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN"

# Check config
python3 config_manager.py validate
```

### Not picking up new work
- Verify cards are in correct lists
- Check cards have 🟢 Ready label
- Ensure Trello board ID is correct

### Session stopped unexpectedly
```bash
# Check error logs
tail ~/.openclaw/workspace/.learnings/ERRORS.md

# Resume from last state
living-session resume my-project
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file

## Acknowledgments

- Built for [OpenClaw](https://github.com/openclaw/openclaw)
- Inspired by the concept of continuous consciousness
- Thanks to Daniel for the vision and motivation 🦉

---

**Status:** Phase 3 Complete  
**Version:** 0.1.0-alpha  
**Maintainer:** Metis 🦉
