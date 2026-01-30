# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a Claude Code configuration repository located at `~/.claude`. It stores:
- User settings and preferences (`settings.json`, `settings.local.json`)
- Session history and conversation data (`history.jsonl`)
- Project-specific settings (`projects/`)
- Plugin configurations (`plugins/`)
- Authentication credentials (`.credentials.json`)
- Session-specific data (todos, file-history, shell-snapshots)

## Repository Structure

**Configuration Files:**
- `settings.json` - Global Claude Code settings (committed to git)
- `settings.local.json` - Machine-specific settings (gitignored)
- `.credentials.json` - Authentication tokens (gitignored, sensitive)

**Session Data (gitignored):**
- `history.jsonl` - Conversation history
- `file-history/` - File edit history per session
- `todos/` - Task lists per session
- `projects/` - Project-specific configuration
- `session-env/` - Environment snapshots per session

**Cached/Temporary (gitignored):**
- `cache/` - Downloaded files and changelogs
- `debug/` - Debug logs and diagnostic data
- `shell-snapshots/` - Shell environment snapshots
- `statsig/` - Analytics and telemetry data

**User Extensions:**
- `plugins/` - Installed plugins and marketplace configurations
- `plans/` - Saved plan mode files

## Git Workflow

This repository tracks Claude Code configuration across machines. The `.gitignore` is configured to:
- **Commit:** Global settings, plugin configurations
- **Ignore:** Session data, local settings, credentials, cache, debug logs

When committing changes:
1. Only commit intentional configuration changes
2. Never commit `.credentials.json` or sensitive data
3. Use descriptive commit messages following the existing style
4. Push changes to sync configuration across machines

## Important Notes

- This is a configuration repository, not a code project
- No build, test, or compilation steps needed
- Changes to `settings.json` take effect immediately (no restart required since v1.0.90)
- Authentication tokens are stored in macOS Keychain (since v0.2.30)
- Remote repository: https://github.com/Thangiee/.claude

## Cost-Optimized Subagent Routing

IMPORTANT: To optimize API costs, automatically delegate subtasks to cheaper models using the Task tool's `model` parameter. Follow these routing rules:

**Use `model: "haiku"` for:**
- Simple questions and explanations
- Formatting code
- Renaming variables/functions
- Writing comments or docstrings
- Simple file searches (Glob, Grep)
- Syntax fixes
- Generating boilerplate

**Use `model: "sonnet"` for:**
- Code review
- Moderate refactoring
- Implementing standard patterns
- Writing tests for existing code
- Debugging straightforward issues
- Multi-file searches and analysis
- Documentation generation

**Keep in main session (no subagent) for:**
- Architecture decisions requiring full conversation context
- Complex debugging needing back-and-forth
- Tasks that build on recent conversation
- Security analysis
- Performance optimization with iterative testing

**Context preservation - do NOT route to cheaper model when:**
- Task depends on previous conversation context
- Working on same files discussed earlier in session
- Follow-up question to previous complex task
- Task references "this", "that", or "the" without specifics (needs context)
- Iterative debugging or refinement

**Example usage:**
```
Task(prompt="Search for all API endpoints", model="haiku", ...)
Task(prompt="Review this function for bugs", model="sonnet", ...)
```
