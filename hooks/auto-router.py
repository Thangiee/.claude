#!/usr/bin/env python3
"""
Claude Code Auto-Router Hook

Intercepts user prompts, classifies complexity with Haiku, and routes to the
cheapest sufficient model.

For SIMPLE/MEDIUM tasks that are pure questions (no file/tool needs):
  → Spawns a separate Claude session with cheaper model

For SIMPLE/MEDIUM tasks that need tools (files, editing, commands):
  → Adds context suggesting use of cheaper subagents

For COMPLEX tasks:
  → Lets through to Opus

Display: 🎯 MEDIUM → Sonnet
Logging: ~/.claude/classifier-log.jsonl
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
VERBOSE_MODE = os.environ.get("CLAUDE_ROUTER_VERBOSE", "0") == "1"
LOG_FILE = Path.home() / ".claude" / "classifier-log.json"
CLASSIFIER_TIMEOUT = 15  # seconds for Haiku classification

# Model mapping
MODEL_MAP = {
    "SIMPLE": "haiku",
    "MEDIUM": "sonnet",
    "COMPLEX": "opus",
}

# Cost per 1M tokens (rough average of input+output)
MODEL_COSTS = {
    "haiku": 1.00,
    "sonnet": 6.00,
    "opus": 30.00,
}

# Patterns that suggest the task needs Claude Code tools (not just text response)
NEEDS_TOOLS_PATTERNS = [
    r'\b(edit|modify|change|update|fix|refactor|add|remove|delete|create|write)\b.*\b(file|code|function|class|method|component)\b',
    r'\b(read|open|look at|check|show|find)\b.*\b(file|files|code|directory|folder)\b',
    r'\brun\b.*\b(test|command|script|build)\b',
    r'\b(implement|build|create|add)\b.*\b(feature|functionality|endpoint|api)\b',
    r'\bgit\b',
    r'\bnpm|yarn|pip|cargo\b',
    r'\.py$|\.js$|\.ts$|\.go$|\.rs$',  # File extensions
    r'src/|lib/|app/|components/',  # Path patterns
]

CLASSIFIER_PROMPT = """Classify this coding task complexity:
- SIMPLE: single function, formatting, rename, obvious fix, simple question, explanation
- MEDIUM: multi-file changes, moderate refactor, standard patterns, code review
- COMPLEX: architecture, concurrency, optimization, design decisions, debugging complex issues

Task: {prompt}

Respond with only: SIMPLE, MEDIUM, or COMPLEX"""


def log_decision(prompt: str, classification: str, model: str, mode: str = "full"):
    """Append decision to log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt_preview": prompt[:50].replace("\n", " ") + ("..." if len(prompt) > 50 else ""),
        "classification": classification,
        "model": model,
        "mode": mode,  # "direct" (subprocess), "full" (let through), "override"
    }
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def display_routing(classification: str, model: str, mode: str = "full"):
    """Print routing decision to stderr (visible to user)."""
    if mode == "override":
        print(f"🎯 Override → {model.capitalize()}", file=sys.stderr)
        return

    if VERBOSE_MODE:
        savings = MODEL_COSTS["opus"] - MODEL_COSTS[model]
        if savings > 0:
            print(f"🎯 Task classified as {classification} complexity", file=sys.stderr)
            print(f"   Model: {model.capitalize()} (saves ~${savings:.2f}/1M tokens vs Opus)", file=sys.stderr)
            if mode == "full":
                print(f"   Mode: Full session (task needs tools)", file=sys.stderr)
        else:
            print(f"🎯 Task classified as {classification} complexity", file=sys.stderr)
            print(f"   Model: {model.capitalize()}", file=sys.stderr)
    else:
        indicator = "→" if mode == "direct" else "⊃"  # ⊃ means "subagent suggested"
        print(f"🎯 {classification} {indicator} {model.capitalize()}", file=sys.stderr)


def needs_tools(prompt: str) -> bool:
    """Check if the prompt likely needs Claude Code tools (file access, bash, etc.)."""
    prompt_lower = prompt.lower()
    for pattern in NEEDS_TOOLS_PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return True
    return False


def classify_with_haiku(prompt: str) -> str:
    """Call Haiku to classify the prompt complexity."""
    classifier_input = CLASSIFIER_PROMPT.format(prompt=prompt[:2000])

    try:
        result = subprocess.run(
            ["claude", "--model", "haiku", "--print", classifier_input],
            capture_output=True,
            text=True,
            timeout=CLASSIFIER_TIMEOUT,
            env={**os.environ, "CLAUDE_ROUTER_SKIP": "1"},  # Prevent recursive hooks
        )

        response = result.stdout.strip().upper()

        for level in ["SIMPLE", "MEDIUM", "COMPLEX"]:
            if level in response:
                return level

        return "MEDIUM"

    except subprocess.TimeoutExpired:
        return "COMPLEX"  # Timeout - be safe
    except Exception:
        return "COMPLEX"  # Error - be safe


def check_override(prompt: str) -> str | None:
    """Check if user specified a model override."""
    # /model command at start
    match = re.match(r"^/model\s+(opus|sonnet|haiku)\b", prompt, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    # Explicit "use X" request
    if re.search(r"\buse\s+opus\b", prompt, re.IGNORECASE):
        return "opus"
    if re.search(r"\buse\s+sonnet\b", prompt, re.IGNORECASE):
        return "sonnet"
    if re.search(r"\buse\s+haiku\b", prompt, re.IGNORECASE):
        return "haiku"

    return None


def run_direct(prompt: str, model: str, cwd: str) -> tuple[bool, str]:
    """Run prompt directly with specified model (for pure questions)."""
    try:
        result = subprocess.run(
            ["claude", "--model", model, "--print", prompt],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
            env={**os.environ, "CLAUDE_ROUTER_SKIP": "1"},
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, result.stdout.strip()
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Request timed out"
    except Exception as e:
        return False, str(e)


def main():
    # Skip if we're in a recursive call
    if os.environ.get("CLAUDE_ROUTER_SKIP") == "1":
        sys.exit(0)

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    cwd = input_data.get("cwd", os.getcwd())

    if not prompt.strip():
        sys.exit(0)

    # Check for manual override
    override = check_override(prompt)
    if override:
        display_routing("OVERRIDE", override, mode="override")
        log_decision(prompt, "OVERRIDE", override, mode="override")
        sys.exit(0)  # Let through with current model

    # Classify the prompt
    classification = classify_with_haiku(prompt)
    target_model = MODEL_MAP[classification]

    # COMPLEX tasks: let through to Opus
    if classification == "COMPLEX":
        display_routing(classification, target_model, mode="full")
        log_decision(prompt, classification, target_model, mode="full")
        sys.exit(0)

    # Check if task needs Claude Code tools
    requires_tools = needs_tools(prompt)

    if requires_tools:
        # Task needs tools - let through but suggest subagent usage
        display_routing(classification, target_model, mode="full")
        log_decision(prompt, classification, target_model, mode="full")

        context = f"""[Auto-Router: This {classification.lower()} task would ideally use {target_model.capitalize()}.
Consider using the Task tool with model="{target_model}" for subtasks to optimize costs.]"""

        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Pure question/explanation - can run directly with cheaper model
    display_routing(classification, target_model, mode="direct")

    success, response = run_direct(prompt, target_model, cwd)

    if success:
        log_decision(prompt, classification, target_model, mode="direct")

        # Include response in the block reason so user can see it
        output = {
            "decision": "block",
            "reason": f"🎯 {classification} → {target_model.capitalize()}\n\n{response}"
        }
        print(json.dumps(output))
        sys.exit(0)
    else:
        # Fallback to full session
        log_decision(prompt, classification, "opus", mode="fallback")
        print(f"Note: {target_model} unavailable, using Opus", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
