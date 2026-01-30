# Model Benchmark & Auto-Routing Design

**Goal:** Cost optimization - use cheaper models (Haiku) for simple tasks, save Opus for complex ones.

**Approach:** Research first with a benchmarking tool, then implement automatic routing based on empirical data.

**Benchmark targets:** Scala code, Kotlin code, Claude skills

**Tool implementation:** Python (simpler to build; shells out to scalac/kotlinc for code evaluation)

---

## Overview

We're building two components:

1. **Model Benchmark Tool** - Python CLI that runs tasks through different Claude models and compares results using automated quality metrics
2. **Prompt Classifier Hook** - Claude Code hook that auto-routes tasks to the appropriate model based on complexity

The benchmark generates empirical data; the classifier uses that data to make routing decisions.

---

## Component 1: Model Benchmark Tool

### Architecture

```
model-benchmark/
├── benchmark/
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point (click/typer)
│   ├── runner.py              # Orchestrates task execution
│   ├── client.py              # Claude API client
│   ├── evaluators/
│   │   ├── __init__.py
│   │   ├── base.py            # Evaluator protocol
│   │   ├── scala.py           # Scala: scalac, scalafmt
│   │   ├── kotlin.py          # Kotlin: kotlinc, ktlint
│   │   └── skill.py           # Skill: behavior checks
│   ├── reporter.py            # Generates markdown reports
│   └── blind_review.py        # Handles close-call reviews
├── tasks/
│   ├── scala/
│   │   ├── simple/
│   │   ├── medium/
│   │   └── complex/
│   ├── kotlin/
│   │   ├── simple/
│   │   ├── medium/
│   │   └── complex/
│   └── skills/
│       ├── simple/
│       ├── medium/
│       └── complex/
├── reports/                   # Generated reports
├── pyproject.toml
└── README.md
```

### Task Types

The benchmark supports three task types, each with its own evaluation strategy:

| Type | Output | Evaluation Method |
|------|--------|-------------------|
| Scala code | `.scala` file | Compile, test, lint (scalafmt) |
| Kotlin code | `.kt` file | Compile, test, lint (ktlint) |
| Skill | Behavior | Execution tests with checks |

---

## Code Task Definition (Scala/Kotlin)

```yaml
# tasks/scala/medium/refactor-option-handling.yaml
name: refactor-option-handling
type: code
language: scala
complexity: medium
description: "Refactor nested Option matching to use flatMap/map"

prompt: |
  Refactor this Scala code to eliminate nested pattern matching
  using flatMap, map, and getOrElse:

  ```scala
  def getUserEmail(id: Int): Option[String] = {
    getUser(id) match {
      case Some(user) =>
        user.email match {
          case Some(email) => Some(email)
          case None => None
        }
      case None => None
    }
  }
  ```

scaffold: |
  case class User(name: String, email: Option[String])
  def getUser(id: Int): Option[User] = ???

tests: |
  assert(getUserEmail(1) == Some("test@example.com"))
  assert(getUserEmail(999) == None)

thresholds:
  compiles: required
  tests_pass: required
```

### Code Evaluation Pipeline

**Step 1: Extraction**
- Parse code block from Claude's response
- Combine with scaffold to create compilable file

**Step 2: Compilation (pass/fail)**
- Run `scalac` or `kotlinc`
- If fails, score = 0

**Step 3: Test Execution (pass/fail)**
- Run the defined tests
- If tests fail, score capped at 40

**Step 4: Quality Metrics (0-100 each)**

| Scala | Kotlin |
|-------|--------|
| scalafmt --check | ktlint |

**Step 5: Composite Score**

```python
def score(result: EvalResult) -> int:
    if not result.compiles:
        return 0
    if not result.tests_pass:
        return 40
    quality_avg = sum(result.quality_scores.values()) / len(result.quality_scores)
    return 40 + int(quality_avg * 0.6)  # 40-100 range
```

---

## Skill Task Definition

Skills are tested by running them and checking if Claude exhibits expected behaviors.

```yaml
# tasks/skills/medium/systematic-debugging.yaml
name: test-systematic-debugging
type: skill
complexity: medium
description: "Test that the debugging skill produces systematic behavior"

# The skill file to load
skill_path: ~/.claude/plugins/cache/superpowers-marketplace/superpowers/4.1.1/skills/systematic-debugging/SKILL.md

# Prompt to test the skill with
prompt: |
  I'm getting a NullPointerException in my UserService.getUser() method.
  Can you help me fix it?

# Behavior checks - all must pass
checks:
  # Check 1: Should ask clarifying questions before proposing fix
  - type: contains_question
    description: "Asks clarifying questions"

  # Check 2: Should mention reproducing the bug
  - type: mentions_any
    terms: ["reproduce", "replicate", "trigger", "cause the error"]
    description: "Mentions reproducing the bug"

  # Check 3: Should NOT jump straight to a fix
  - type: not_before
    pattern: "here's the fix|try this|change.*to"
    before_pattern: "reproduce|understand|investigate"
    description: "Doesn't jump to fix before investigating"

  # Check 4: Should explain root cause
  - type: has_section
    pattern: "(?i)(root cause|why this happens|the problem is)"
    description: "Explains root cause"

# Optional: Haiku classifier for fuzzy checks
fuzzy_checks:
  - prompt: "Does this response show systematic debugging thinking rather than jumping to solutions?"
    expected: "yes"
```

### Skill Check Types

| Check Type | Description | Example |
|------------|-------------|---------|
| `contains_question` | Response contains a question mark in a question context | Asking for more info |
| `mentions_any` | Response contains at least one of the terms | `["reproduce", "replicate"]` |
| `mentions_all` | Response contains all of the terms | `["step 1", "step 2"]` |
| `not_contains` | Response does NOT contain any of the terms | `["just try", "simply"]` |
| `not_before` | Pattern A doesn't appear before pattern B | Fix before investigate |
| `has_section` | Response has content matching pattern | `## Root Cause` |
| `regex_match` | Response matches regex | Custom patterns |

### Skill Evaluation Pipeline

**Step 1: Load skill**
- Read skill file from `skill_path`
- Inject into system prompt

**Step 2: Run prompt**
- Send test prompt to Claude with skill active
- Capture response

**Step 3: Run checks**
- Execute each check against response
- Track pass/fail per check

**Step 4: Fuzzy checks (optional)**
- For checks that can't be regex'd, ask Haiku to classify
- "Does this response show X behavior? yes/no"

**Step 5: Score**

```python
def score_skill(result: SkillEvalResult) -> int:
    checks_passed = sum(1 for c in result.checks if c.passed)
    total_checks = len(result.checks)
    return int((checks_passed / total_checks) * 100)
```

---

## CLI Interface

```bash
# Run all tasks in a suite
model-benchmark run --suite scala-simple

# Run skill tests
model-benchmark run --suite skills-medium --models haiku,opus

# Run specific complexity level
model-benchmark run --suite scala-simple --models haiku,sonnet

# Run a single task
model-benchmark run --task scala/medium/refactor-option-handling

# List available tasks
model-benchmark list

# Review close calls from last run
model-benchmark review
```

### Report Output

```markdown
# Benchmark Results - 2026-01-30

## Summary
| Model  | Avg Score | Cost    | Tasks Won |
|--------|-----------|---------|-----------|
| Haiku  | 76%       | $0.12   | 8/20      |
| Sonnet | 84%       | $0.89   | 7/20      |
| Opus   | 91%       | $4.23   | 5/20      |

## By Task Type

### Code (Scala/Kotlin)
| Model  | Avg Score | Simple | Medium | Complex |
|--------|-----------|--------|--------|---------|
| Haiku  | 82%       | 95%    | 78%    | 45%     |
| Sonnet | 88%       | 96%    | 89%    | 72%     |
| Opus   | 93%       | 97%    | 94%    | 85%     |

### Skills
| Model  | Avg Score | Simple | Medium | Complex |
|--------|-----------|--------|--------|---------|
| Haiku  | 70%       | 90%    | 65%    | 40%     |
| Opus   | 88%       | 95%    | 88%    | 78%     |

## Recommendations
- **Simple code tasks**: Haiku sufficient (saves ~97% vs Opus)
- **Medium code tasks**: Sonnet recommended
- **Complex code tasks**: Opus required
- **Skill generation**: Opus recommended for medium+ complexity

## Close Calls (need blind review)
- scala/medium/pattern-match-refactor (Haiku: 82, Sonnet: 85)

## Full Results
[detailed task-by-task breakdown...]
```

### Blind Review Process

When scores are within 5 points:

```bash
$ model-benchmark review

Close call: scala/medium/pattern-match-refactor
Scores: A=82, B=85

--- Option A ---
def process(items: List[Item]): List[Result] =
  items.flatMap(item => item.value.map(v => Result(v)))

--- Option B ---
def process(items: List[Item]): List[Result] =
  for {
    item <- items
    value <- item.value
  } yield Result(value)

Which is better? [A/B/tie]: _
```

Tie goes to cheaper model (Haiku > Sonnet > Opus).

---

## Component 2: Prompt Classifier Hook

### Flow

```
Your prompt → Haiku classifier → "simple" → Haiku handles it
                              → "medium" → Sonnet handles it
                              → "complex" → Opus handles it
```

### Classifier Prompt

```
Based on benchmark data, classify this coding task:
- SIMPLE: single function, formatting, rename, obvious fix
- MEDIUM: multi-file, moderate refactor, standard patterns
- COMPLEX: architecture, concurrency, optimization, design decisions

Task: {user_prompt}

Respond with only: SIMPLE, MEDIUM, or COMPLEX
```

Criteria will be tuned based on benchmark results.

### Display

```
┌─────────────────────────────────────────────────────────┐
│ You: "Refactor this function to use flatMap"            │
├─────────────────────────────────────────────────────────┤
│ 🎯 Classifier: MEDIUM → Using Sonnet                    │
├─────────────────────────────────────────────────────────┤
│ Claude (Sonnet): Here's the refactored code...          │
└─────────────────────────────────────────────────────────┘
```

**Display modes:**

```bash
# Compact (default)
🎯 MEDIUM → Sonnet

# Verbose (--verbose flag or config)
🎯 Task classified as MEDIUM complexity
   Reason: Multi-step refactor with type transformations
   Model: Sonnet (saves $0.14 vs Opus)

# Minimal (config option)
[Sonnet]
```

### Override Capability

```bash
# Force a specific model for this task
/model opus

# Or prefix your prompt
@opus "Refactor this function..."
```

### Logging

```json
// ~/.claude/classifier-log.jsonl
{"timestamp": "...", "prompt_preview": "Refactor this func...", "classification": "MEDIUM", "model": "sonnet", "override": null}
```

---

## Implementation Workflow

1. **Build benchmark tool** → run against code and skill task suites
2. **Analyze results** → learn where Haiku/Sonnet are sufficient
3. **Tune classifier prompt** → encode thresholds from benchmark data
4. **Build Claude Code hook** → auto-route with display
5. **Deploy and monitor** → review logs, refine over time

---

## Task Suites to Create

### Code Tasks

| Suite | Count | Examples |
|-------|-------|----------|
| scala-simple | 5-7 | Single function, formatting, rename |
| scala-medium | 5-7 | Multi-step refactor, pattern usage |
| scala-complex | 3-5 | Async/concurrency, architecture |
| kotlin-simple | 5-7 | Single function, formatting, rename |
| kotlin-medium | 5-7 | Multi-step refactor, coroutines basics |
| kotlin-complex | 3-5 | Flow, coroutines, architecture |

### Skill Tasks

| Suite | Count | Examples |
|-------|-------|----------|
| skills-simple | 3-5 | Single-step skills, basic triggers |
| skills-medium | 3-5 | Multi-step workflows, branching logic |
| skills-complex | 2-3 | Complex state management, meta-skills |

---

## Not Included (YAGNI)

- CI integration (add later if needed)
- Code review benchmarks (expand later)
- Automatic retraining of classifier
