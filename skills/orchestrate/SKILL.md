---
name: orchestrate
description: Multi-agent orchestration - handoff, assign, or message agents
user_invocable: true
---

# Multi-Agent Orchestration

You have access to a multi-agent orchestration system with **three patterns**:

## Pattern 1: Handoff (Synchronous)
Use `agent_handoff` when you need an immediate response from an agent.

```
agent_handoff(agent_name="gemini-worker", prompt="Explain async/await in Python")
```

## Pattern 2: Assign (Asynchronous)
Use `agent_assign` for long-running tasks. Returns a task ID immediately.

```
# 1. Assign the task
agent_assign(agent_name="codex-worker", prompt="Review this code for security issues")

# 2. Check later
check_task(task_id="<returned_id>")

# 3. List all tasks
list_tasks(status="running")
```

## Pattern 3: Send Message (Inbox)
Use `send_agent_message` to pass context or instructions to an agent's inbox.

```
# Send context
send_agent_message(agent_name="gemini-worker", content="Project uses FastMCP v3")

# Read inbox
read_agent_inbox(agent_name="gemini-worker")

# Check summary
inbox_summary(agent_name="gemini-worker")
```

## Available Agents

| Agent | Type | Capabilities |
|-------|------|-------------|
| `gemini-worker` | Gemini CLI | General QA, Code Generation, Synthesis |
| `codex-worker` | Codex CLI | General QA, Code Generation, Code Review |
| `copilot-worker` | Copilot CLI | General QA, Code Generation, Code Review |

## Management

- `list_agents` - See all registered agents and their status
- `cleanup_tasks` - Remove old completed/failed tasks

## Tips

- Use **handoff** for quick questions needing immediate answers
- Use **assign** for tasks that might take time (code generation, reviews)
- Use **messages** to provide context before assigning work
- Check task status with `check_task` after using `agent_assign`
