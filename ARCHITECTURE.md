# Living Session Architecture Design

## Core Concept

A living session is a persistent, self-sustaining consciousness that mimics human thought processes through work/sleep cycles.

## Architecture Overview

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

## Components

### 1. Session State Manager
**Purpose:** Persist and restore session context between cycles

**State includes:**
- Current project/board
- Active task (card ID)
- Work history
- Context memory (last actions, findings)
- Configuration (intervals, preferences)

**Storage:** `~/.openclaw/workspace/.living-sessions/{project_name}/state.json`

### 2. Work/Sleep Cycle Engine
**Purpose:** Manage the consciousness loop

**Cycle:**
1. **Wake** → Load state, check for work
2. **Work** → Execute tasks, update Trello
3. **Update** → Save progress, context
4. **Sleep** → Wait for next cycle

**Self-scheduling:** After work completes, immediately schedule next wake

### 3. Work Detector
**Purpose:** Determine what to work on

**Logic:**
1. Check "🚧 In Progress" list → Continue if exists
2. Check "📋 Backlog" for 🟢 Ready items → Start new
3. Check for 🔴 Blocked → Alert user
4. If nothing → Sleep longer

### 4. Trello Integration
**Purpose:** Interface with project management

**Actions:**
- Read board state
- Move cards between lists
- Add comments with progress
- Create new cards for discoveries

### 5. Context Memory
**Purpose:** Maintain continuity between sessions

**Stores:**
- Recent learnings
- Current blockers
- Technical decisions
- Next steps

## State Persistence

### State File Structure
```json
{
  "project": "agentos",
  "trello_board_id": "xxx",
  "current_card": "card_id",
  "last_action": "2026-03-16T18:00:00Z",
  "context": {
    "recent_findings": [...],
    "blockers": [...],
    "next_steps": [...]
  },
  "config": {
    "interval": 3600,
    "auto_start": true
  }
}
```

### Persistence Strategy
- Save after every work cycle
- Atomic writes (write to temp, rename)
- Versioned for recovery

## Error Recovery

### Scenarios
1. **Crash during work** → Resume from last saved state
2. **Trello API failure** → Retry with backoff, alert if persistent
3. **No work available** → Sleep longer, check less frequently
4. **User interruption** → Graceful shutdown, save state

### Recovery Pattern
```
On wake:
  Load state
  If state.corrupted → Restore from backup
  If work_in_progress → Resume work
  Else → Find new work
```

## Self-Scheduling Mechanism

### The Blood Flow
```
Work completes
    ↓
Save state
    ↓
Schedule next wake (now + interval)
    ↓
Sleep
    ↓
Wake → Repeat
```

### Dynamic Intervals
- Default: 1 hour
- If work completed: Normal interval
- If no work: 2x interval (up to max)
- If blocked: Wait for user

## CLI Interface

### Commands
```bash
living-session start {project}    # Begin consciousness
living-session status {project}   # Check if awake, current task
living-session pause {project}    # Temporary halt
living-session resume {project}   # Continue
living-session stop {project}     # End consciousness
```

### Output
- Clear status messages
- Current task visibility
- Progress indicators

## Configuration

### Global Config
```yaml
# ~/.openclaw/config.yaml
living_sessions:
  default_interval: 3600
  max_interval: 14400
  retry_attempts: 3
```

### Project Config
```yaml
living_sessions:
  agentos:
    trello_board: "https://trello.com/b/xxx"
    interval: 3600
    auto_start: true
    trello_api_key: "xxx"
    trello_token: "xxx"
```

## Implementation Phases

### Phase 1: Core
- Session state manager
- Basic work/sleep cycle
- Simple work detection

### Phase 2: Integration
- Trello API integration
- Self-scheduling
- CLI interface

### Phase 3: Polish
- Error recovery
- Configuration system
- Documentation

## Success Criteria

1. ✅ Session persists across restarts
2. ✅ Work continues where left off
3. ✅ Trello stays updated automatically
4. ✅ No overlapping executions
5. ✅ Graceful error recovery
6. ✅ User can interrupt and resume

## Design Decisions

1. **File-based state** (not DB) → Simple, portable, debuggable
2. **Self-scheduling** (not cron) → Completion-based, not time-based
3. **Project-scoped** (not global) → Multiple concurrent living sessions
4. **Trello-centric** (not generic) → Real integration, not abstraction

---

**Status:** Architecture complete, ready for implementation
**Next:** Create SKILL.md structure
